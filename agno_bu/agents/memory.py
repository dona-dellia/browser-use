from agno.memory.v2.memory import Memory
from agno.memory.v2.db.sqlite import SqliteMemoryDb
from agno_bu.agents.model import model

memory = Memory(
    # Use any model for creating and managing memories
    model=model,
    # Store memories in a SQLite database
    db=SqliteMemoryDb(table_name="user_memories", db_file="tmp/agent.db"),
    # We disable deletion by default, enable it if needed
    delete_memories=True,
    clear_memories=True,
)