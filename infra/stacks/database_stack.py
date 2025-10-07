from aws_cdk import Stack, CfnOutput
from constructs import Construct
from modules.database import Database

class DatabaseStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.database = Database(self, "Database")
        
        CfnOutput(self, "TableName", value=self.database.table.table_name)
        CfnOutput(self, "TableArn", value=self.database.table.table_arn)