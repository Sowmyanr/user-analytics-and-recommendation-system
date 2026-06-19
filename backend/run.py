"""
Development server startup script
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Start the development server"""
    
    # Check if we're in the right directory
    if not Path("app").exists():
        print("❌ Error: Please run this script from the backend directory")
        print("   Current directory should contain the 'app' folder")
        sys.exit(1)
    
    # Check if virtual environment is activated
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  Warning: Virtual environment not detected")
        print("   Consider activating your virtual environment first")
        print("   Run: venv\\Scripts\\activate (Windows) or source venv/bin/activate (Linux/Mac)")
        
        response = input("\nContinue anyway? (y/N): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    # Check if .env file exists
    if not Path(".env").exists():
        print("⚠️  Warning: .env file not found")
        if Path(".env.example").exists():
            print("   Copying .env.example to .env...")
            import shutil
            shutil.copy(".env.example", ".env")
            print("   ✅ .env file created. Please review and update the settings.")
        else:
            print("   Please create a .env file with your configuration")
    
    print("🚀 Starting Punjab Rozgar Portal Backend...")
    print("📡 Server will be available at: http://localhost:8000")
    print("📖 API Documentation: http://localhost:8000/api/docs")
    print("🔧 Health Check: http://localhost:8000/health")
    print("\n" + "="*50)
    
    try:
        # Start the server
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "app.main:app",
            "--reload",
            "--host", "0.0.0.0",
            "--port", "8000"
        ], check=True)
    
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error starting server: {e}")
        print("\nTroubleshooting tips:")
        print("1. Make sure all dependencies are installed: pip install -r requirements.txt")
        print("2. Check if port 8000 is already in use")
        print("3. Verify your .env file configuration")
        sys.exit(1)

if __name__ == "__main__":
    main()
