import os
from app import create_app
from config import get_config, print_config_summary

# Create app instance with appropriate config
config = get_config()
app = create_app(config)

if __name__ == '__main__':
    # Print configuration summary
    print_config_summary()
    
    # Get port from environment or use default
    port = int(os.environ.get('PORT', 5000))
    
    # Get host from environment or use default
    host = os.environ.get('HOST', '0.0.0.0')
    
    # Run the app
    print(f"🚀 Starting Mobile Shop ERP on http://{host}:{port}")
    app.run(host=host, port=port, debug=app.config['DEBUG'])