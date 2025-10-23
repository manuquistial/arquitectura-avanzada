#!/usr/bin/env python3
"""
Test script to verify Azure Blob Storage and OpenTelemetry connections in the pod.
Based on the actual mintic-client implementation.
"""

import asyncio
import json
import logging
import os
import sys
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_opentelemetry():
    """Test OpenTelemetry availability and configuration using mintic-client implementation."""
    logger.info("🔍 Testing OpenTelemetry connection...")
    
    try:
        # Test OpenTelemetry availability (same as in client.py)
        from opentelemetry import metrics, trace
        OTEL_AVAILABLE = True
        logger.info("✅ OpenTelemetry packages imported successfully")
        
        # Test tracer (same as in client.py)
        tracer = trace.get_tracer("mintic_client", "1.0.0")
        logger.info("✅ OpenTelemetry tracer created")
        
        # Test metrics (same as in client.py)
        meter = metrics.get_meter("mintic_client")
        
        # Create test metrics (same pattern as in client.py)
        test_counter = meter.create_counter(
            name="test.calls",
            description="Test calls counter",
            unit="1"
        )
        
        test_histogram = meter.create_histogram(
            name="test.latency",
            description="Test latency histogram",
            unit="s"
        )
        
        # Test span creation (same as in client.py)
        with tracer.start_span(name="test.span", kind=trace.SpanKind.CLIENT) as span:
            span.set_attribute("test.attribute", "test_value")
            span.set_status(trace.Status(trace.StatusCode.OK))
            logger.info("✅ OpenTelemetry span created and completed")
        
        # Test metrics recording
        test_counter.add(1, {"test": "value"})
        test_histogram.record(0.1, {"test": "value"})
        logger.info("✅ OpenTelemetry metrics recorded")
        
        return {
            "status": "success",
            "otel_available": True,
            "tracer": True,
            "metrics": True,
            "instrumentation": True
        }
        
    except ImportError as e:
        logger.error(f"❌ OpenTelemetry import failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "otel_available": False,
            "tracer": False,
            "metrics": False,
            "instrumentation": False
        }
    except Exception as e:
        logger.error(f"❌ OpenTelemetry test failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "otel_available": False,
            "tracer": False,
            "metrics": False,
            "instrumentation": False
        }

async def test_azure_blob_storage():
    """Test Azure Blob Storage connection using mintic-client implementation."""
    logger.info("🔍 Testing Azure Blob Storage connection...")
    
    try:
        from app.client import MinTICClient
        from app.config import Settings
        
        settings = Settings()
        client = MinTICClient(settings)
        
        logger.info(f"📡 Document service URL: {settings.document_url}")
        
        # Test the _get_document_sas_url method (same as in client.py)
        try:
            # This will test the document service connection
            document_url = await client._get_document_sas_url("test-document-id")
            logger.info(f"✅ SAS URL generated: {document_url[:50]}...")
            
            # Test if the SAS URL is accessible
            try:
                import httpx
                async with httpx.AsyncClient(timeout=5.0) as http_client:
                    blob_response = await http_client.get(document_url)
                    logger.info(f"✅ Azure Blob Storage accessible: {blob_response.status_code}")
                    return {
                        "status": "success",
                        "document_service": True,
                        "sas_url_generated": True,
                        "blob_accessible": True,
                        "blob_status_code": blob_response.status_code
                    }
            except Exception as blob_e:
                logger.warning(f"⚠️  Blob access failed: {blob_e}")
                return {
                    "status": "partial_success",
                    "document_service": True,
                    "sas_url_generated": True,
                    "blob_accessible": False,
                    "blob_error": str(blob_e)
                }
                
        except Exception as e:
            logger.error(f"❌ Document service test failed: {e}")
            return {
                "status": "error",
                "document_service": False,
                "error": str(e)
            }
                
    except ImportError as e:
        logger.error(f"❌ Required packages not available: {e}")
        return {
            "status": "error",
            "error": f"Import error: {e}"
        }
    except Exception as e:
        logger.error(f"❌ Azure Blob Storage test failed: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

async def test_environment_variables():
    """Test environment variables configuration."""
    logger.info("🔍 Testing environment variables...")
    
    try:
        from app.config import Settings
        
        settings = Settings()
        
        env_vars = {
            "REDIS_HOST": settings.redis_host,
            "REDIS_PORT": settings.redis_port,
            "REDIS_PASSWORD": "***" if settings.redis_password else "NOT_SET",
            "REDIS_SSL": settings.redis_ssl,
            "REDIS_ENABLED": settings.redis_enabled,
            "DB_HOST": settings.database_host,
            "DB_PORT": settings.database_port,
            "DB_NAME": settings.database_name,
            "DB_USER": settings.database_user,
            "DB_PASSWORD": "***" if settings.database_password else "NOT_SET",
            "DOCUMENT_URL": settings.document_url,
            "METADATA_URL": settings.metadata_url,
            "CITIZEN_URL": settings.citizen_url,
            "TRANSFER_URL": settings.transfer_url,
            "SIGNATURE_URL": settings.signature_url,
            "HUB_URL": settings.hub_url,
            "OPERATOR_ID": settings.operator_id,
            "ENVIRONMENT": settings.environment
        }
        
        logger.info("📋 Environment variables:")
        for key, value in env_vars.items():
            logger.info(f"  {key}: {value}")
        
        return {
            "status": "success",
            "variables": env_vars
        }
        
    except Exception as e:
        logger.error(f"❌ Environment variables test failed: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

async def test_redis_connection():
    """Test Redis connection using mintic-client implementation."""
    logger.info("🔍 Testing Redis connection...")
    
    try:
        from app.client import MinTICClient
        from app.config import Settings
        
        settings = Settings()
        client = MinTICClient(settings)
        
        # Test Redis connection using mintic-client's redis_client
        redis_client = client.redis_client
        
        # Test connection
        await redis_client.connect()
        
        if redis_client.client:
            # Test basic operations
            await redis_client.set("test_key", "test_value", ttl=60)
            value = await redis_client.get("test_key")
            
            if value == "test_value":
                logger.info("✅ Redis connection and operations working")
                return {
                    "status": "success",
                    "connected": True,
                    "operations": True
                }
            else:
                logger.warning("⚠️  Redis operations failed")
                return {
                    "status": "partial_success",
                    "connected": True,
                    "operations": False
                }
        else:
            logger.error("❌ Redis client not available")
            return {
                "status": "error",
                "connected": False,
                "operations": False
            }
            
    except Exception as e:
        logger.error(f"❌ Redis test failed: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

async def test_database_connection():
    """Test database connection using mintic-client implementation."""
    logger.info("🔍 Testing database connection...")
    
    try:
        from app.database import get_db
        from app.config import Settings
        
        settings = Settings()
        
        # Test database connection
        db = next(get_db())
        
        if db:
            # Test basic query
            result = db.execute("SELECT 1 as test")
            row = result.fetchone()
            
            if row and row[0] == 1:
                logger.info("✅ Database connection and operations working")
                return {
                    "status": "success",
                    "connected": True,
                    "operations": True
                }
            else:
                logger.warning("⚠️  Database operations failed")
                return {
                    "status": "partial_success",
                    "connected": True,
                    "operations": False
                }
        else:
            logger.error("❌ Database connection failed")
            return {
                "status": "error",
                "connected": False,
                "operations": False
            }
            
    except Exception as e:
        logger.error(f"❌ Database test failed: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

async def test_mintic_hub_connection():
    """Test MinTIC Hub connection using mintic-client implementation."""
    logger.info("🔍 Testing MinTIC Hub connection...")
    
    try:
        from app.client import MinTICClient
        from app.config import Settings
        
        settings = Settings()
        client = MinTICClient(settings)
        
        logger.info(f"📡 MinTIC Hub URL: {settings.mintic_base_url}")
        
        # Test a simple hub call (validateCitizen with a test ID)
        try:
            result = await client.validate_citizen(12345678)
            logger.info(f"✅ MinTIC Hub connection working: {result.status}")
            return {
                "status": "success",
                "hub_connected": True,
                "hub_response": result.status,
                "hub_message": result.message
            }
        except Exception as e:
            logger.warning(f"⚠️  MinTIC Hub call failed: {e}")
            return {
                "status": "partial_success",
                "hub_connected": False,
                "hub_error": str(e)
            }
            
    except Exception as e:
        logger.error(f"❌ MinTIC Hub test failed: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

async def main():
    """Run all connection tests."""
    logger.info("🚀 Starting Azure connections test...")
    
    results = {}
    
    # Test environment variables
    results["environment"] = await test_environment_variables()
    
    # Test OpenTelemetry
    results["opentelemetry"] = await test_opentelemetry()
    
    # Test Redis
    results["redis"] = await test_redis_connection()
    
    # Test Database
    results["database"] = await test_database_connection()
    
    # Test Azure Blob Storage
    results["azure_blob_storage"] = await test_azure_blob_storage()
    
    # Test MinTIC Hub
    results["mintic_hub"] = await test_mintic_hub_connection()
    
    # Summary
    logger.info("📊 Test Results Summary:")
    logger.info("=" * 50)
    
    for service, result in results.items():
        status = result.get("status", "unknown")
        emoji = "✅" if status == "success" else "⚠️" if status == "partial_success" else "❌"
        logger.info(f"{emoji} {service.upper()}: {status}")
    
    # Overall status
    all_success = all(r.get("status") == "success" for r in results.values())
    partial_success = any(r.get("status") == "partial_success" for r in results.values())
    
    if all_success:
        logger.info("🎉 All tests passed!")
        return 0
    elif partial_success:
        logger.info("⚠️  Some tests had issues but core functionality works")
        return 1
    else:
        logger.error("❌ Critical tests failed")
        return 2

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
