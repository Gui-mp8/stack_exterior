# Configuracao AWS e GitHub

Este guia prepara a entrega `GitHub Actions -> ECR -> ECS Fargate`. O GitHub usa
OIDC e credenciais temporarias; nenhuma access key da AWS deve ser criada para o
pipeline.

## 1. Defina os valores

Substitua os exemplos antes de executar os comandos:

```bash
export AWS_REGION="us-east-1"
export AWS_ACCOUNT_ID="SEU_ACCOUNT_ID"
export GITHUB_OWNER="SEU_USUARIO_OU_ORG"
export GITHUB_REPOSITORY="stack_exterior"
export VPC_ID="vpc-..."
```

## 2. Crie ECR, ECS e CloudWatch Logs

```bash
aws ecr create-repository \
  --repository-name stack-exterior-dbt \
  --image-scanning-configuration scanOnPush=true \
  --region "$AWS_REGION"

aws ecs create-cluster \
  --cluster-name stack-exterior \
  --region "$AWS_REGION"

aws logs create-log-group \
  --log-group-name /ecs/stack-exterior-dbt \
  --region "$AWS_REGION"
```

Se algum recurso ja existir, apenas confirme seu nome no console.

## 3. Prepare a rede do Fargate

Use pelo menos duas subnets. Para este projeto de aprendizado, a configuracao
mais simples e usar subnets publicas, security group apenas com trafego de saida
e `assign_public_ip = ENABLED`. Em producao, prefira subnets privadas com NAT ou
VPC endpoints para ECR, S3, CloudWatch Logs, Athena, Glue e STS.

Copie os IDs de subnet e security group para `ECS_DBT_CONFIG` em
`airflow/include/settings.py`.

## 4. Configure as roles do ECS

Crie no IAM a role `stack-exterior-ecs-execution`, usando o caso de uso
`Elastic Container Service Task`. Anexe a policy gerenciada
`AmazonECSTaskExecutionRolePolicy`. Essa role e usada pelo Fargate para baixar a
imagem e publicar logs.

Para a task role, este projeto reutiliza a role existente:

```bash
arn:aws:iam::181027095791:role/AWSCustomGlueRole
```

Essa role sera definida como `taskRoleArn` e entregara credenciais temporarias
ao dbt dentro do container. Confirme que sua trust policy permite tambem o
principal `ecs-tasks.amazonaws.com`; uma role que confia somente em
`glue.amazonaws.com` nao pode ser assumida por uma task ECS. Preserve qualquer
principal Glue que ja exista ao adicionar o ECS.

Confirme tambem que a `AWSCustomGlueRole` possui permissoes para executar queries
no Athena, criar/alterar tabelas no Glue e ler/gravar nos prefixes Bronze, Silver,
Gold e de resultados no S3. Se Lake Formation estiver governando as tabelas,
conceda as permissoes de banco/tabela para essa mesma role.

## 5. Configure OIDC do GitHub

No IAM, acesse `Identity providers -> Add provider`:

- Provider type: `OpenID Connect`
- Provider URL: `https://token.actions.githubusercontent.com`
- Audience: `sts.amazonaws.com`

Crie a role `stack-exterior-github-actions` confiando nesse provider. Restrinja a
trust policy ao subject
`repo:GITHUB_OWNER/GITHUB_REPOSITORY:ref:refs/heads/main`.

A role precisa de permissoes para autenticar e publicar no ECR, registrar e
consultar ECS Task Definitions e executar `iam:PassRole` somente para
`stack-exterior-ecs-execution` e `AWSCustomGlueRole`.

## 6. Configure as GitHub Actions Variables

No repositorio GitHub, abra `Settings -> Secrets and variables -> Actions ->
Variables` e cadastre:

| Variable | Exemplo |
|---|---|
| `AWS_GITHUB_ACTIONS_ROLE_ARN` | `arn:aws:iam::123456789012:role/stack-exterior-github-actions` |
| `AWS_REGION` | `us-east-1` |
| `ECR_REPOSITORY` | `stack-exterior-dbt` |
| `ECS_TASK_FAMILY` | `stack-exterior-dbt` |
| `ECS_CONTAINER_NAME` | `stack-exterior-dbt` |
| `ECS_EXECUTION_ROLE_ARN` | ARN da execution role |
| `S3_BUCKET` | `modern-data-platform-guilherme-2026` |
| `BRONZE_DATABASE` | `stack_exterior_bronze` |
| `ATHENA_WORKGROUP` | `primary` |

Nao e preciso cadastrar `AWS_ACCESS_KEY_ID` ou `AWS_SECRET_ACCESS_KEY` no
GitHub. O workflow ja define a task role como
`arn:aws:iam::181027095791:role/AWSCustomGlueRole`.

## 7. Autorize o Airflow a executar Fargate

Na identidade usada pela conexao `aws_default` do Airflow, permita
`ecs:RunTask`, `ecs:DescribeTasks`, `ecs:DescribeTaskDefinition`, `ecs:ListTasks`,
`logs:GetLogEvents` e `iam:PassRole` para as duas roles da Task Definition.

No `airflow/include/settings.py`, preencha:

- `subnets`
- `security_groups`
- `assign_public_ip`, conforme a rede escolhida

O Airflow referencia apenas a familia `stack-exterior-dbt`. Quando o workflow
registra uma revisao nova, o proximo `RunTask` usa a revisao ativa mais recente.

## 8. Primeiro deploy e teste

Envie uma alteracao da pasta `dbt/` ao branch `main`, acompanhe o workflow
`dbt ECS` e confirme uma nova revisao em `ECS -> Task definitions`.

Para um teste direto antes do Airflow:

```bash
aws ecs run-task \
  --cluster stack-exterior \
  --launch-type FARGATE \
  --task-definition stack-exterior-dbt \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-...],securityGroups=[sg-...],assignPublicIp=ENABLED}" \
  --overrides '{"containerOverrides":[{"name":"stack-exterior-dbt","command":["debug"]}]}'
```

Depois execute `dag_stack_silver` no Airflow. Em caso de sucesso, o Asset Silver
dispara `dag_stack_gold`.
