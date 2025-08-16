import os
from urllib.parse import quote_plus

class AzureMongoConfig:
    def __init__(self):
        # Azure Cosmos DB MongoDB API connection details
        self.cosmos_endpoint = os.getenv('AZURE_COSMOS_ENDPOINT')
        self.cosmos_key = os.getenv('AZURE_COSMOS_KEY')
        self.database_name = os.getenv('AZURE_COSMOS_DB_NAME', 'smarthome')
        
        # SSL and authentication settings for Azure Cosmos DB
        self.ssl_enabled = True
        self.auth_source = 'admin'
        self.retry_writes = False  # Azure Cosmos DB doesn't support retryWrites
        
    def get_connection_string(self):
        """Generate Azure Cosmos DB MongoDB connection string"""
        if not self.cosmos_endpoint or not self.cosmos_key:
            raise ValueError("Azure Cosmos DB credentials not found in environment variables")
        
        # URL encode the key to handle special characters
        encoded_key = quote_plus(self.cosmos_key)
        
        connection_string = (
            f"mongodb://{self.cosmos_endpoint}:{encoded_key}@{self.cosmos_endpoint}.mongo.cosmos.azure.com:10255/"
            f"{self.database_name}?ssl=true&replicaSet=globaldb&retrywrites=false&maxIdleTimeMS=120000&appName=@{self.cosmos_endpoint}@"
        )
        
        return connection_string
    
    def get_connection_params(self):
        """Get connection parameters for PyMongo client"""
        return {
            'host': self.get_connection_string(),
            'tls': True,
            'tlsAllowInvalidCertificates': True,
            'serverSelectionTimeoutMS': 30000,
            'socketTimeoutMS': 30000,
            'connectTimeoutMS': 30000,
            'maxPoolSize': 50
        }
