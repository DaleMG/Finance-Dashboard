from database.database import (
    initialize_database,
    add_category,
    get_categories
)

initialize_database()

add_category("Groceries")
add_category("Fuel")

print(get_categories())