"""Construct App."""

import os
from typing import Any, Dict, List, Optional

from aws_cdk import App, CfnOutput, Duration, Stack, Tags
from aws_cdk import aws_apigatewayv2_alpha as apigw
from aws_cdk import aws_cloudwatch as cloudwatch
from aws_cdk import aws_cloudwatch_actions as cloudwatch_actions
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_efs as efs
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda
from aws_cdk import aws_logs as logs
from aws_cdk import aws_sns as sns
from aws_cdk import aws_sns_subscriptions as subscriptions
from aws_cdk.aws_apigatewayv2_integrations_alpha import HttpLambdaIntegration
from config import StackSettings
from constructs import Construct

settings = StackSettings()


DEFAULT_ENV = {
    "GDAL_CACHEMAX": "200",  # 200 mb
    "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
    "GDAL_INGESTED_BYTES_AT_OPEN": "32768",  # get more bytes when opening the files.
    "GDAL_HTTP_MERGE_CONSECUTIVE_RANGES": "YES",
    "GDAL_HTTP_MULTIPLEX": "YES",
    "GDAL_HTTP_VERSION": "2",
    "PYTHONWARNINGS": "ignore",
    "VSI_CACHE": "TRUE",
    "VSI_CACHE_SIZE": "5000000",  # 5 MB (per file-handle)
}


class LambdaStack(Stack):
    """Lambda Stack"""

    def __init__(
        self,
        scope: Construct,
        id: str,
        memory: int = 1024,
        timeout: int = 30,
        runtime: aws_lambda.Runtime = aws_lambda.Runtime.PYTHON_3_10,
        concurrent: Optional[int] = None,
        permissions: Optional[List[iam.PolicyStatement]] = None,
        environment: Optional[Dict] = None,
        context_dir: str = "../../",
        **kwargs: Any,
    ) -> None:
        """Define stack."""
        super().__init__(scope, id, *kwargs)

        permissions = permissions or []
        environment = environment or {}

        vpc = ec2.Vpc(self, "MyVPC",
            max_azs=2,  # Default is all AZs in the region
            nat_gateways=1,
            cidr="10.0.0.0/16",
            # Define custom CIDR range for each subnet type
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_NAT,
                    cidr_mask=24
                ),
            ],
        )


        # Create and attach a file system
        file_system = efs.FileSystem(
            self,
            "EfsFileSystem",
            vpc=vpc,
            lifecycle_policy=efs.LifecyclePolicy.AFTER_7_DAYS,  # Or choose another policy
            performance_mode=efs.PerformanceMode.GENERAL_PURPOSE,
        )

        access_point = file_system.add_access_point(
            "AccessPoint",
            path="/export/lambda",
            create_acl={"owner_uid": "1001", "owner_gid": "1001", "permissions": "750"},
            posix_user={
                "uid": "1001",
                "gid": "1001",
            },
        )

        lambda_function = aws_lambda.Function(
            self,
            f"{id}-lambda",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_NAT),
            runtime=runtime,
            code=aws_lambda.Code.from_docker_build(
                path=os.path.abspath(context_dir),
                file="infrastructure/aws/lambda/Dockerfile",
                platform="linux/amd64",
            ),
            handler="handler.handler",
            memory_size=memory,
            reserved_concurrent_executions=concurrent,
            timeout=Duration.seconds(timeout),
            environment={**DEFAULT_ENV, **environment},
            log_retention=logs.RetentionDays.ONE_WEEK,
            filesystem=aws_lambda.FileSystem.from_efs_access_point(
                access_point, "/mnt/efs"
            ),  # Mounting it to /mnt/efs in Lambda
        )

        file_system.connections.allow_default_port_from(lambda_function)
        file_system.grant(
            lambda_function,
            "elasticfilesystem:ClientMount",
            "elasticfilesystem:ClientWrite",
        )

        for perm in permissions:
            lambda_function.add_to_role_policy(perm)

        api = apigw.HttpApi(
            self,
            f"{id}-endpoint",
            default_integration=HttpLambdaIntegration(
                f"{id}-integration", lambda_function
            ),
        )

        # Create an SNS Topic
        if settings.alarm_email:
            topic = sns.Topic(
                self,
                f"{id}-500-Errors",
                display_name=f"{id} Gateway 500 Errors",
                topic_name=f"{id}-Gateway-500-Errors",
            )
            # Subscribe email to the topic
            email_address = settings.alarm_email
            topic.add_subscription(subscriptions.EmailSubscription(email_address))

            # Create CloudWatch Alarm
            alarm = cloudwatch.Alarm(
                self,
                "MyAlarm",
                metric=cloudwatch.Metric(
                    namespace="AWS/ApiGateway",
                    metric_name="5XXError",
                    dimensions_map={"ApiName": f"{id}-endpoint"},
                    period=Duration.minutes(1),
                ),
                evaluation_periods=1,
                threshold=1,
                alarm_description="Alarm if 500 errors are detected",
                alarm_name=f"{id}-ApiGateway500Alarm",
                actions_enabled=True,
            )
            alarm.add_alarm_action(cloudwatch_actions.SnsAction(topic))
        CfnOutput(self, "Endpoint", value=api.url)


app = App()

perms = []
if settings.buckets:
    perms.append(
        iam.PolicyStatement(
            actions=["s3:GetObject"],
            resources=[f"arn:aws:s3:::{bucket}*" for bucket in settings.buckets],
        )
    )


lambda_stack = LambdaStack(
    app,
    f"{settings.name}-{settings.stage}",
    memory=settings.memory,
    timeout=settings.timeout,
    concurrent=settings.max_concurrent,
    permissions=perms,
    environment=settings.additional_env,
)
# Tag infrastructure
for key, value in {
    "Project": settings.name,
    "Stack": settings.stage,
    "Owner": settings.owner,
    "Client": settings.client,
}.items():
    if value:
        Tags.of(lambda_stack).add(key, value)


app.synth()
