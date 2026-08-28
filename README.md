# Stack Exterior

Projeto de aprendizado de uma plataforma de dados moderna na AWS, usando
Airflow 3, S3, Apache Iceberg, Glue Data Catalog, Athena, dbt e ECS Fargate.

## Arquitetura

```text
DockerOperator -> S3 Bronze (Iceberg) -> Glue Catalog
                         |
                    Asset Bronze
                         v
Airflow -> ECS Fargate -> dbt Silver (Athena + Iceberg)
                         |
                    Asset Silver
                         v
Airflow -> ECS Fargate -> dbt Gold (Athena + Iceberg)
```

O S3 guarda os arquivos de dados e metadados Iceberg. O Glue guarda o catalogo
e o ponteiro para o metadata atual. Athena executa o SQL gerado pelo dbt. O ECS
Fargate fornece apenas o compute temporario para o container dbt.

## Componentes

- `src/`: gerador de dados Bronze com PyArrow e PyIceberg.
- `dbt/`: imagem dbt-athena e modelos Silver/Gold em Iceberg.
- `airflow/`: DAGs Airflow 3, TaskGroups e Assets.
- `.github/workflows/dbt-ecs.yml`: valida, publica no ECR e registra a task ECS.
- `docs/AWS_GITHUB_SETUP.md`: configuracao completa de AWS e GitHub OIDC.

## Fluxo das camadas

`dag_test_stack_bronze` executa o gerador local, grava as tabelas `customers`,
`orders` e `order_items` em `s3://modern-data-platform-guilherme-2026/bronze/`
e valida seu registro no Glue.

Quando a Bronze termina, o Asset `BRONZE_READY` dispara `dag_stack_silver`. Essa
DAG roda `dbt build --select path:models/silver` no Fargate. O sucesso publica
`SILVER_READY`, que dispara `dag_stack_gold` e seus modelos analiticos.

## Modelos dbt

Silver:

- `stg_customers`: padronizacao e deduplicacao de clientes.
- `stg_orders`: padronizacao e deduplicacao de pedidos.
- `stg_order_items`: tipagem monetaria e deduplicacao dos itens.

Gold:

- `fct_daily_sales`: receita agregada por dia, canal, pagamento e categoria.
- `dim_customer_value`: pedidos e valor acumulado por cliente.

Todos os modelos sao materializados como Iceberg. Os modelos Silver usam
`merge`, portanto exigem Athena engine version 3.

O adapter usa `schema_table_unique` para criar uma localizacao S3 nova a cada
reconstrucao das tabelas Gold e realizar a troca de metadados sem indisponibilidade.

## Configuracao da AWS

### AWS CLI

Instale a AWS CLI v2 no Linux x86_64:

```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

Confirme a instalacao e configure o acesso local:

```bash
aws --version
aws configure
```

Informe `AWS Access Key ID`, `AWS Secret Access Key`, regiao `us-east-1` e
formato de saida `json`. As credenciais ficam no perfil local da AWS e nao devem
ser enviadas ao repositorio. Valide a identidade configurada:

```bash
aws sts get-caller-identity
```

A instalacao para outras arquiteturas e sistemas operacionais esta na
[documentacao oficial da AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html).

### Roles do ECS

A Task Definition usa duas roles com responsabilidades diferentes:

- `stack-exterior-ecs-execution`: execution role usada pelo Fargate para baixar
  a imagem do ECR e publicar logs no CloudWatch. Deve confiar em
  `ecs-tasks.amazonaws.com` e possuir a policy gerenciada
  `AmazonECSTaskExecutionRolePolicy`.
- `AWSCustomGlueRole`: task role entregue ao container dbt. Deve confiar em
  `ecs-tasks.amazonaws.com` e possuir acesso ao Athena, Glue e aos prefixes
  Bronze, Silver, Gold e de resultados no S3. Caso a role continue sendo usada
  por Glue Jobs, preserve tambem `glue.amazonaws.com` na trust policy.

A task role utilizada neste projeto e:

```text
arn:aws:iam::181027095791:role/AWSCustomGlueRole
```

Quem registra ou executa a Task Definition tambem precisa de `iam:PassRole`
para essas duas roles. A identidade usada pelo Airflow precisa ainda de
`ecs:RunTask`, `ecs:DescribeTasks`, `ecs:DescribeTaskDefinition`, `ecs:ListTasks`
e `logs:GetLogEvents`.

### GitHub Actions

O deploy usa OIDC, portanto nao requer access keys armazenadas no GitHub. No
IAM, crie o identity provider com:

```text
Provider URL: https://token.actions.githubusercontent.com
Audience: sts.amazonaws.com
```

A role `stack-exterior-github-actions` deve confiar nesse provider e restringir
o subject ao repositorio e branch usados no deploy:

```text
repo:Gui-mp8/stack_exterior:ref:refs/heads/main
```

Essa role precisa publicar imagens no ECR, registrar e consultar Task
Definitions no ECS e executar `iam:PassRole` para
`stack-exterior-ecs-execution` e `AWSCustomGlueRole`.

Em `Settings -> Secrets and variables -> Actions -> Variables` no repositorio
GitHub, configure:

- `AWS_GITHUB_ACTIONS_ROLE_ARN`
- `AWS_REGION`
- `ECR_REPOSITORY`
- `ECS_TASK_FAMILY`
- `ECS_CONTAINER_NAME`
- `ECS_EXECUTION_ROLE_ARN`
- `S3_BUCKET`
- `BRONZE_DATABASE`
- `ATHENA_WORKGROUP`

Os comandos para criar ECR, cluster ECS, log group e executar o primeiro teste
estao em [`docs/AWS_GITHUB_SETUP.md`](docs/AWS_GITHUB_SETUP.md).

## Desenvolvimento local

Imagem do gerador Bronze:

```bash
docker build -t stack-exterior-gerador:latest .
```

Imagem dbt:

```bash
docker build -t stack-exterior-dbt:local dbt
```

Validacao do projeto dbt sem conectar na AWS:

```bash
docker run --rm stack-exterior-dbt:local parse --no-partial-parse
```

Airflow local:

```bash
cd airflow
astro dev start
```

Antes de executar as DAGs Silver/Gold, configure os IDs de subnet e security
group em `airflow/include/settings.py` e siga o guia
[`docs/AWS_GITHUB_SETUP.md`](docs/AWS_GITHUB_SETUP.md).

## Credenciais

As credenciais locais da AWS continuam no `airflow/.env`, que nao deve ser
versionado. No Fargate, o dbt recebe credenciais temporarias pela IAM task role.
No GitHub, o workflow usa OIDC e tambem nao armazena access keys.

A IAM task role usada pelo dbt no Fargate e
`arn:aws:iam::181027095791:role/AWSCustomGlueRole`. Ela deve confiar no principal
`ecs-tasks.amazonaws.com`, alem de possuir acesso ao Athena, Glue e aos prefixes
do projeto no S3.
