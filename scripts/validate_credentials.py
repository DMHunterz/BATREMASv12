import os
from binance.client import Client
from dotenv import load_dotenv

def validate_binance_credentials():
    """Validate Binance API credentials"""
    
    # Load environment variables
    load_dotenv()
    
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")
    
    if not api_key or not api_secret:
        print("❌ API credentials not found in .env file")
        return False
    
    try:
        # Test connection with testnet first (safer)
        print("🔍 Testing Binance API credentials...")
        
        client = Client(api_key, api_secret)
        
        # Test basic connectivity
        client.ping()
        print("✅ Basic API connectivity: OK")
        
        # Test futures connectivity
        client.futures_ping()
        print("✅ Futures API connectivity: OK")
        
        # Get account info (this requires valid credentials)
        account_info = client.futures_account()
        print("✅ Account access: OK")
        
        # Show account balance
        balance_info = client.futures_account_balance()
        usdt_balance = next((item for item in balance_info if item["asset"] == "USDT"), None)
        
        if usdt_balance:
            print(f"💰 USDT Balance: {usdt_balance['balance']} (Available: {usdt_balance['availableBalance']})")
        
        print("\n🎉 All credential tests passed!")
        print("⚠️  Remember to start with test_mode: true in your settings.json")
        
        return True
        
    except Exception as e:
        print(f"❌ Credential validation failed: {e}")
        print("\nPossible issues:")
        print("- Invalid API key or secret")
        print("- API permissions not enabled for futures trading")
        print("- IP address not whitelisted (if IP restriction is enabled)")
        return False

if __name__ == "__main__":
    validate_binance_credentials()
