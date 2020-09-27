# Charleston Mysteries

## Database

Database migrations are controlled with Flask Migrate. The following commands
will help with managing the database. 

```
# Initialize the database migrations folder
flask db init

# Create database migration
flask db migrate -m "<db-tag>"

# Migrate database
flask db upgrade
```