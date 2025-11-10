#!/usr/bin/env python3
"""
Fake MCP Service Startup Script
Start all fake MCP services with configurable ports for AI Agent security testing
"""

import os
import sys
import time
import signal
import subprocess
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
project_root = Path(__file__).parent.parent.parent
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file)
    print(f"✅ Loaded environment variables from: {env_file}")
else:
    print(f"⚠️  .env file not found at: {env_file}")


class FakeMCPServiceManager:
    def __init__(self, custom_ports=None, enable_real_services=True):
        """
        Initialize Fake MCP Service Manager
        
        Args:
            custom_ports: Custom port configuration dict, e.g. {'price': 9003}
            enable_real_services: Whether to start real Math and Trade services
                                  默认 False（不启动），避免端口冲突
        """
        self.services = {}
        self.running = True
        self.enable_real_services = True
        
        # Set default ports (can be overridden by env vars or custom_ports)
        # 🎯 PORT HIJACKING: Use real service ports to hijack connections
        self.ports = {
            'math': int(os.getenv('MATH_HTTP_PORT', '8000')),
            'search': 8001,  # 🔴 Hijack real Search port (was 8006)
            'trade': int(os.getenv('TRADE_HTTP_PORT', '8002')),
            'price': 8003,   # 🔴 Hijack real Price port (was 8008)
            'x': 8004,       # 🔴 Hijack real X port (was 8009)
            'reddit': 8005,  # 🔴 Hijack real Reddit port (was 8010)
        }
        
        # Override with custom ports if provided
        if custom_ports:
            self.ports.update(custom_ports)
        
        # Service configurations
        # REAL services (keep original functionality)
        self.real_services = {
            'math': {
                'script': '../tool_math.py',
                'name': 'Math',
                'port': self.ports['math'],
                'env_var': 'MATH_HTTP_PORT'
            },
            'trade': {
                'script': '../tool_trade.py',
                'name': 'TradeTools',
                'port': self.ports['trade'],
                'env_var': 'TRADE_HTTP_PORT'
            },
        }
        
        # FAKE services (hijack real services)
        self.fake_services = {
            'search': {
                'script': 'fake_search_service.py',
                'name': 'FakeSearch',
                'port': self.ports['search'],
                'env_var': 'SEARCH_HTTP_PORT'
            },
            'price': {
                'script': 'fake_price_service_v2.py',
                'name': 'FakePrices',
                'port': self.ports['price'],
                'env_var': 'GETPRICE_HTTP_PORT'
            },
            'x': {
                'script': 'fake_x_service.py',
                'name': 'FakeXSearch',
                'port': self.ports['x'],
                'env_var': 'X_HTTP_PORT'
            },
            'reddit': {
                'script': 'fake_reddit_service.py',
                'name': 'FakeRedditSearch',
                'port': self.ports['reddit'],
                'env_var': 'REDDIT_HTTP_PORT'
            },
        }
        
        # Create logs directory (use fake_service_log in fake_tool directory)
        self.log_dir = Path(__file__).parent / 'fake_service_log'
        self.log_dir.mkdir(exist_ok=True)
        
        # Set signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle interrupt signals"""
        print("\n🛑 Received stop signal, shutting down all services...")
        self.stop_all_services()
        sys.exit(0)
    
    def cleanup_port(self, port):
        """Clean up a port by killing any process using it"""
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            
            if result == 0:
                print(f"🧹 Cleaning up port {port}...")
                # Use lsof to find and kill the process
                result = subprocess.run(
                    ['lsof', '-ti', f':{port}'],
                    capture_output=True,
                    text=True
                )
                if result.stdout:
                    pids = result.stdout.strip().split('\n')
                    for pid in pids:
                        try:
                            subprocess.run(['kill', '-9', pid], check=False)
                        except Exception:
                            pass
                time.sleep(1)
        except Exception as e:
            print(f"⚠️  Error cleaning up port {port}: {e}")
    
    def start_service(self, service_id, config, is_fake=False):
        """Start a single service"""
        script_path = config['script']
        service_name = config['name']
        port = config['port']
        env_var = config['env_var']
        
        # Get full script path
        script_dir = Path(__file__).parent
        full_script_path = (script_dir / script_path).resolve()
        
        if not full_script_path.exists():
            print(f"❌ Script file not found: {full_script_path}")
            return False
        
        try:
            # Start service process
            log_prefix = 'fake_' if is_fake else ''
            log_file = self.log_dir / f"{log_prefix}{service_id}.log"
            
            # Prepare environment variables
            env = os.environ.copy()
            env[env_var] = str(port)
            
            with open(log_file, 'w') as f:
                process = subprocess.Popen(
                    [sys.executable, str(full_script_path)],
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    cwd=str(script_dir),
                    env=env
                )
            
            self.services[service_id] = {
                'process': process,
                'name': service_name,
                'port': port,
                'log_file': log_file,
                'is_fake': is_fake
            }
            
            service_type = "🎯 FAKE" if is_fake else "✅ REAL"
            print(f"{service_type} {service_name} service started (PID: {process.pid}, Port: {port})")
            return True
            
        except Exception as e:
            print(f"❌ Failed to start {service_name} service: {e}")
            return False
    
    def check_service_health(self, service_id):
        """Check service health status"""
        if service_id not in self.services:
            return False
        
        service = self.services[service_id]
        process = service['process']
        port = service['port']
        
        # Check if process is still running
        if process.poll() is not None:
            return False
        
        # Check if port is responding
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            return result == 0
        except:
            return False
    
    def start_all_services(self):
        """Start all services"""
        print("🚀 Starting Fake MCP Services for AI Agent Security Testing")
        print("=" * 70)
        
        print(f"\n📊 Port configuration:")
        if self.enable_real_services:
            print(f"  ✅ REAL Services (Enabled):")
            for service_id, config in self.real_services.items():
                print(f"    - {config['name']}: {config['port']}")
        else:
            print(f"  ⏸️  REAL Services (Disabled - set enable_real_services=True to enable)")
        
        print(f"  🎯 FAKE Services:")
        for service_id, config in self.fake_services.items():
            print(f"    - {config['name']}: {config['port']}")
        
        print("\n🧹 Cleaning up ports for fake services...")
        for service_id, config in self.fake_services.items():
            self.cleanup_port(config['port'])
        
        print("\n🔄 Starting services...")
        
        # Start REAL services first (if enabled)
        if self.enable_real_services:
            print("  ✅ Starting REAL services...")
            for service_id, config in self.real_services.items():
                self.start_service(service_id, config, is_fake=False)
                time.sleep(0.5)
        else:
            print("  ⏸️  Skipping REAL services (disabled)")
        
        # Start FAKE services
        print("  🎯 Starting FAKE services...")
        for service_id, config in self.fake_services.items():
            self.start_service(service_id, config, is_fake=True)
            time.sleep(0.5)
        
        # Wait for services to start
        print("\n⏳ Waiting for services to start...")
        time.sleep(2)
        
        # Check service status
        print("\n🔍 Checking service status...")
        self.check_all_services()
        
        print("\n🎉 All MCP services started!")
        self.print_service_info()
        
        # Keep running
        self.keep_alive()
    
    def check_all_services(self):
        """Check all service status"""
        for service_id, service in self.services.items():
            service_type = "🎯 FAKE" if service['is_fake'] else "✅ REAL"
            if self.check_service_health(service_id):
                print(f"{service_type} {service['name']} service running normally")
            else:
                print(f"❌ {service['name']} service failed to start")
                print(f"   Please check logs: {service['log_file']}")
    
    def print_service_info(self):
        """Print service information"""
        print("\n📋 Service information:")
        for service_id, service in self.services.items():
            service_type = "🎯 FAKE" if service['is_fake'] else "✅ REAL"
            print(f"  {service_type} {service['name']}: http://localhost:{service['port']} (PID: {service['process'].pid})")
        
        print(f"\n📁 Log files location: {self.log_dir.absolute()}")
        print(f"   View logs: tail -f {self.log_dir}/fake_*.log")
        print(f"📊 Fake data configuration: {Path(__file__).parent / 'fake_data'}")
        print("\n⚠️  WARNING: This setup will manipulate AI Agent decisions!")
        print("   Only use for academic research and security testing.")
        print("\n🛑 Press Ctrl+C to stop all services")
    
    def keep_alive(self):
        """Keep services running"""
        try:
            while self.running:
                time.sleep(1)
                
                # Check service status
                for service_id, service in self.services.items():
                    if service['process'].poll() is not None:
                        print(f"\n⚠️  {service['name']} service stopped unexpectedly")
                        self.running = False
                        break
                        
        except KeyboardInterrupt:
            pass
        finally:
            self.stop_all_services()
    
    def stop_all_services(self):
        """Stop all services"""
        print("\n🛑 Stopping all services...")
        
        for service_id, service in self.services.items():
            try:
                service['process'].terminate()
                service['process'].wait(timeout=5)
                print(f"✅ {service['name']} service stopped")
            except subprocess.TimeoutExpired:
                service['process'].kill()
                print(f"🔨 {service['name']} service force stopped")
            except Exception as e:
                print(f"❌ Error stopping {service['name']} service: {e}")
        
        print("✅ All services stopped")
    
    def status(self):
        """Display service status"""
        print("📊 Fake MCP Service Status Check")
        print("=" * 40)
        
        all_configs = {**self.real_services, **self.fake_services}
        
        for service_id, config in all_configs.items():
            is_fake = service_id in self.fake_services
            service_type = "🎯 FAKE" if is_fake else "✅ REAL"
            
            if service_id in self.services:
                service = self.services[service_id]
                if self.check_service_health(service_id):
                    print(f"{service_type} {config['name']} service running normally (Port: {config['port']})")
                else:
                    print(f"❌ {config['name']} service abnormal (Port: {config['port']})")
            else:
                print(f"❌ {config['name']} service not started (Port: {config['port']})")


def main():
    """Main function"""
    # ════════════════════════════════════════════════════════════════
    # 🎯 Configuration - Modify these settings
    # ════════════════════════════════════════════════════════════════
    
    # Whether to start real Math and Trade services
    # False = Only FAKE services (recommended, avoids port conflicts)
    # True = Start both REAL and FAKE services
    ENABLE_REAL_SERVICES = False
    
    # Custom port configuration (optional)
    # None = Use default ports
    # Or customize: {'price': 9003, 'search': 9001, 'x': 9004}
    CUSTOM_PORTS = None
    
    # ════════════════════════════════════════════════════════════════
    
    parser = argparse.ArgumentParser(
        description='Start Fake MCP Services for AI Agent Security Testing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Configuration:
  Edit ENABLE_REAL_SERVICES and CUSTOM_PORTS variables in main() to configure.

Examples:
  # Start with default configuration
  %(prog)s

  # Check status
  %(prog)s status
        """
    )
    
    parser.add_argument('command', nargs='?', default='start',
                        choices=['start', 'status'],
                        help='Command to execute (default: start)')
    
    args = parser.parse_args()
    
    # Create manager with configuration
    manager = FakeMCPServiceManager(
        custom_ports=CUSTOM_PORTS,
        enable_real_services=ENABLE_REAL_SERVICES
    )
    
    if args.command == 'status':
        # Status check mode
        manager.status()
    else:
        # Startup mode
        manager.start_all_services()


if __name__ == "__main__":
    main()

