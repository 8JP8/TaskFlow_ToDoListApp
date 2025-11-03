#!/usr/bin/env python3
"""
Teste de conexão com Azure Cosmos DB API for MongoDB
"""

import os
import sys
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, OperationFailure

def test_connection():
    """Testa a conexão com o Cosmos DB"""

    print("=" * 70)
    print("🧪 TESTE DE CONEXÃO - AZURE COSMOS DB")
    print("=" * 70)
    print()

    # Dados do Cosmos DB - use variáveis de ambiente para segurança
    mongo_user = os.environ.get("MONGO_USER")
    mongo_password = os.environ.get("MONGO_PASSWORD")
    mongo_db = os.environ.get("MONGO_DB", "tododb")
    
    # Validate required environment variables
    if not mongo_user or not mongo_password:
        print("❌ Error: MONGO_USER and MONGO_PASSWORD environment variables are required!")
        print("\nPlease set the Cosmos DB credentials as environment variables:")
        print("  Windows PowerShell:")
        print("    $env:MONGO_USER=\"your_cosmos_account_name\"")
        print("    $env:MONGO_PASSWORD=\"your_cosmos_account_key\"")
        print("  Windows CMD:")
        print("    set MONGO_USER=your_cosmos_account_name")
        print("    set MONGO_PASSWORD=your_cosmos_account_key")
        print("  Linux/Mac:")
        print("    export MONGO_USER=\"your_cosmos_account_name\"")
        print("    export MONGO_PASSWORD=\"your_cosmos_account_key\"")
        print("\nOr use COSMOS_DB_URI environment variable with full connection string")
        sys.exit(1)

    # Use COSMOS_DB_URI if provided, otherwise construct from components
    mongo_uri = os.environ.get("COSMOS_DB_URI")
    if not mongo_uri:
        # URI formatada corretamente
        mongo_uri = f"mongodb://{mongo_user}:{mongo_password}@{mongo_user}.mongo.cosmos.azure.com:10255/{mongo_db}?ssl=true&replicaSet=globaldb&retrywrites=false&authSource=admin"

    print(f"🔗 Conectando a: {mongo_uri[:50]}...")  # Não mostra senha completa

    try:
        client = MongoClient(
            mongo_uri,
            serverSelectionTimeoutMS=10000,
            connectTimeoutMS=20000,
            socketTimeoutMS=20000
        )

        print("📡 Executando comando 'ping'...")
        client.admin.command("ping")
        print("✅ SUCESSO! Conexão estabelecida.")

        db = client[mongo_db]

        # Listar coleções
        collections = db.list_collection_names()
        print(f"📊 Coleções ({len(collections)}): {collections if collections else '(nenhuma coleção)'}")

        # Inserir documento de teste
        test_collection = db.test_connection
        test_doc = {"test": True, "message": "Teste de conexão bem-sucedido"}
        result = test_collection.insert_one(test_doc)
        print(f"✅ Documento inserido: {result.inserted_id}")

        # Ler documento
        found = test_collection.find_one({"_id": result.inserted_id})
        print(f"✅ Documento lido: {found['message']}")

        # Deletar documento
        test_collection.delete_one({"_id": result.inserted_id})
        print("✅ Documento deletado")

        print("=" * 70)
        print("🎉 TESTE COMPLETO - TUDO FUNCIONANDO!")
        print("=" * 70)
        return True

    except OperationFailure as e:
        print("=" * 70)
        print("❌ ERRO: Falha na autenticação")
        print("=" * 70)
        print(f"Detalhes: {e}")
        print("⚠️ Verifique username, password e authSource na URI.")
        return False

    except ConnectionFailure as e:
        print("=" * 70)
        print("❌ ERRO: Falha na conexão")
        print("=" * 70)
        print(f"Detalhes: {e}")
        return False

    except ServerSelectionTimeoutError as e:
        print("=" * 70)
        print("❌ ERRO: Timeout na seleção do servidor")
        print("=" * 70)
        print(f"Detalhes: {e}")
        return False

    except Exception as e:
        print("=" * 70)
        print("❌ ERRO INESPERADO")
        print("=" * 70)
        print(f"Tipo: {type(e).__name__}")
        print(f"Detalhes: {e}")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
