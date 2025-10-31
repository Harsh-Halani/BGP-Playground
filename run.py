"""
BGP Playground Application Entry Point
Main script to run the application
"""

import os
import sys
import logging
from app import create_app
from app.config import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Main application entry point"""
    # Get environment
    env = os.environ.get('FLASK_ENV', 'development')
    
    # Create application
    config_class = config.get(env, config['default'])
    app = create_app(config_class)
    
    # Log startup information
    logger.info(f"Starting BGP Playground in {env} mode")
    logger.info(f"Debug mode: {app.config['DEBUG']}")
    logger.info(f"Host: {app.config['HOST']}")
    logger.info(f"Port: {app.config['PORT']}")
    
    # Run application
    try:
        app.run(
            host=app.config['HOST'],
            port=app.config['PORT'],
            debug=app.config['DEBUG']
        )
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Application error: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
