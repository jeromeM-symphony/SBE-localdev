# SBE services local development

## How to start SBE stack

### Services
This stack is able to start most of SBE services backend:
    - mongodb
    - bigtable
    - pubsub
    - redis 

To start the all stack:
```shell
docker compose up
```

To start only one service (redis, bigtable, pubsub):
```shell
docker compose up redis
```

To stop all services of the stack:
```shell
docker compose down -v
```

## Configuration of services

To initialise all tables, topics, subscriptions and all mongoDB data, the only needed thing is to run:
```bash
init_datastores.sh
```

For **MongoDB** as the mongo definition changes, you may have to run the script to update the database from the old version to the new one. To do this, use the SBE-Mongo repository and use the localdev par to run it locally.

### Specific servies

#### PubSub

# Install the dependency once
pip install google-cloud-pubsub

# Run with defaults
python setup_pubsub.py

# Preview changes without touching the emulator
python setup_pubsub.py --dry-run

# Override host or project if needed
python setup_pubsub.py --host localhost:9985 --project my-other-project


#### Bigtable

# Install dependency
pip install google-cloud-bigtable

# Run
python setup_bigtable.py --instance your-instance-id

# Dry-run to preview
python setup_bigtable.py --instance your-instance-id --dry-run