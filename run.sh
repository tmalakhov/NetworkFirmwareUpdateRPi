# Set the path variable for the server script

export FLASK_APP='rpi_server/app/routes.py'

# Run the server with external access enabled

python3 -m flask run --host=0.0.0.0
