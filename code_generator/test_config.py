# test_config.py
from config.settings import settings

def test_configuration():
    """Test the configuration setup"""
    
    print("🧪 Testing Configuration...")
    
    # Print current configuration
    settings.print_configuration()
    
    # Validate configuration
    validation = settings.validate_configuration()
    
    print(f"\n📋 Validation Results:")
    print(f"   Valid: {validation['valid']}")
    
    if validation["errors"]:
        print("   Errors:")
        for error in validation["errors"]:
            print(f"     - {error}")
    
    if validation["warnings"]:
        print("   Warnings:")
        for warning in validation["warnings"]:
            print(f"     - {warning}")
    
    # Test provider config
    try:
        provider_config = settings.get_current_provider_config()
        print(f"\n🔧 Provider Config:")
        print(f"   Provider: {provider_config['provider']}")
        print(f"   Base URL: {provider_config['base_url']}")
        print(f"   Model: {provider_config['model_name']}")
        print(f"   Auth Required: {provider_config['requires_auth']}")
        
    except Exception as e:
        print(f"❌ Provider config error: {e}")

if __name__ == "__main__":
    test_configuration()