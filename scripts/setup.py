import os

def setup_project():
    """Setup the project structure and directories"""
    
    # Create logs directory if it doesn't exist
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        print(f"✅ Created {log_dir} directory")
    else:
        print(f"📁 {log_dir} directory already exists")
    
    # Create config directory if it doesn't exist
    config_dir = 'config'
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
        print(f"✅ Created {config_dir} directory")
    else:
        print(f"📁 {config_dir} directory already exists")
    
    print("\n🚀 Project setup complete!")
    print("\nNext steps:")
    print("1. Copy .env.example to .env and add your Binance API credentials")
    print("2. Install dependencies: pip install -r requirements.txt")
    print("3. Review and adjust config/settings.json as needed")
    print("4. Run the bot: python scripts/main.py")
    print("\n⚠️  IMPORTANT: Start with test_mode: true in settings.json!")

if __name__ == "__main__":
    setup_project()
