from app.db.connections import get_db_connection


async def create_user_conversation_table(email: str):
    conn = None
    try:
        conn = await get_db_connection()
        
        table_name = f"conversations_{email.replace('@', '_').replace('.', '_')}"
        create_table_query = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id SERIAL PRIMARY KEY,
                project_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        
        await conn.execute(create_table_query)

    except Exception as e:
        print(f"An error occurred while creating the table: {e}")
    finally:
        if conn:
            await conn.close()

async def store_conversation_in_db(email: str, project_id: str, role: str, content: str):
    conn = None
    try:
        conn = await get_db_connection()
        
        await create_user_conversation_table(email)
        
        table_name = f"conversations_{email.replace('@', '_').replace('.', '_')}"
        insert_query = f"""
            INSERT INTO {table_name} (project_id, role, content)
            VALUES ($1, $2, $3)
        """
        
        await conn.execute(insert_query, project_id, role, content)

    except Exception as e:
        print(f"An error occurred while storing the conversation: {e}")
    finally:
        if conn:
            await conn.close()

async def get_conversation_history_from_db(email: str, project_id: str) -> list[dict[str, str]]:
    conn = None
    try:
        conn = await get_db_connection()
        
        table_name = f"conversations_{email.replace('@', '_').replace('.', '_')}"
        
        # Check if the table exists
        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = $1
            )
        """, table_name)
        
        if not table_exists:
            # If the table doesn't exist, create it
            await create_user_conversation_table(email)


        select_query = f"""
            WITH ranked_messages AS (
                SELECT role, content, created_at,
                       ROW_NUMBER() OVER (ORDER BY created_at DESC) as row_num
                FROM {table_name}
                WHERE project_id = $1
            )
            SELECT role, content
            FROM ranked_messages
            WHERE row_num <= 10
            ORDER BY created_at ASC
        """
        
        results = await conn.fetch(select_query, project_id)
        return [{"role": row["role"], "content": row["content"]} for row in results]

    except Exception as e:
        print(f"An error occurred while retrieving the conversation: {e}")
        return []
    finally:
        if conn:
            await conn.close()

async def create_user_pin_table(email: str):
    conn = None
    try:
        conn = await get_db_connection()
        
        table_name = f"pins_{email.replace('@', '_').replace('.', '_')}"
        create_table_query = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id SERIAL PRIMARY KEY,
                project_id TEXT NOT NULL,
                topic_name TEXT NOT NULL,
                pin_content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        
        await conn.execute(create_table_query)

    except Exception as e:
        print(f"An error occurred while creating the pin table: {e}")
    finally:
        if conn:
            await conn.close()

async def create_pin_in_db(email: str, project_id: str, topic_name: str, pin_content: str):
    conn = None
    try:
        conn = await get_db_connection()
        
        await create_user_pin_table(email)
        
        table_name = f"pins_{email.replace('@', '_').replace('.', '_')}"
        insert_query = f"""
            INSERT INTO {table_name} (project_id, topic_name, pin_content)
            VALUES ($1, $2, $3)
        """
        
        await conn.execute(insert_query, project_id, topic_name, pin_content)

    except Exception as e:
        print(f"An error occurred while storing the pin: {e}")
    finally:
        if conn:
            await conn.close()

async def delete_pin_from_db(email: str, pin_id: int):
    conn = None
    try:
        conn = await get_db_connection()
        
        # Construct the table name using the user's email
        table_name = f"pins_{email.replace('@', '_').replace('.', '_')}"
        
        # Prepare the delete query for the specific pin by id
        delete_query = f"DELETE FROM {table_name} WHERE id = $1"
        
        # Execute the delete query
        result = await conn.execute(delete_query, pin_id)
        
        # Check if a record was deleted
        if result == "DELETE 0":
            print(f"No pin with id {pin_id} found for user {email}")
            raise Exception(f"No pin with id {pin_id} found for user {email}")

    except Exception as e:
        print(f"An error occurred while deleting the pin: {e}")
    finally:
        if conn:
            await conn.close()

async def get_pins_from_db(email: str, project_id: str):
    conn = None
    try:
        conn = await get_db_connection()
        
        # Construct the table name using the user's email
        table_name = f"pins_{email.replace('@', '_').replace('.', '_')}"
        
        # Prepare the select query to fetch pins based on project_id
        select_query = f"SELECT * FROM {table_name} WHERE project_id = $1"
        
        # Execute the query and fetch results
        pins = await conn.fetch(select_query, project_id)
        
        return pins

    except Exception as e:
        print(f"An error occurred while fetching the pins: {e}")
        return None
    finally:
        if conn:
            await conn.close()

async def create_assistants_table():
    conn = None
    try:
        conn = await get_db_connection()
        
        create_table_query = """
            CREATE TABLE IF NOT EXISTS assistants_table (
                id SERIAL PRIMARY KEY,
                project_id TEXT NOT NULL,
                assistant_name TEXT NOT NULL,
                thread_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (project_id, assistant_name)
            )
        """
        
        await conn.execute(create_table_query)

    except Exception as e:
        print(f"An error occurred while creating the assistants table: {e}")
    finally:
        if conn:
            await conn.close()

async def insert_new_thread(project_id: str, assistant_name: str, thread_id: str):
    conn = None
    try:
        conn = await get_db_connection()

        insert_query = """
            INSERT INTO assistants_table (project_id, assistant_name, thread_id)
            VALUES ($1, $2, $3)
            ON CONFLICT (project_id, assistant_name)
            DO NOTHING
        """

        await conn.execute(insert_query, project_id, assistant_name, thread_id)
        print("New thread inserted successfully.")

    except Exception as e:
        print(f"An error occurred while inserting the new thread: {e}")
    finally:
        if conn:
            await conn.close()

async def get_thread(project_id: str, assistant_name: str):
    conn = None
    try:
        conn = await get_db_connection()
        await create_assistants_table()

        query_check_thread = """
            SELECT thread_id FROM assistants_table 
            WHERE project_id = $1 AND assistant_name = $2
        """
        
        row = await conn.fetchrow(query_check_thread, project_id, assistant_name)
        
        if row and row['thread_id']:
            return row['thread_id']
        else:
            return "thread does not exist"

    except Exception as e:
        print(f"An error occurred while fetching the thread: {e}")
    finally:
        if conn:
            await conn.close()

async def update_thread_id(project_id: str, thread_id: str, assistant_name: str):
    conn = None
    try:
        conn = await get_db_connection()
        await create_assistants_table()

        query_update_thread = """
            UPDATE assistants_table
            SET thread_id = $1
            WHERE project_id = $2 AND assistant_name = $3
        """

        # Use 'execute' and then fetch the number of rows affected
        result = await conn.execute(query_update_thread, thread_id, project_id, assistant_name)

        # The execute result typically returns a string like 'UPDATE <number>'
        affected_rows = result.split()[-1]

        if affected_rows == '0':
            await insert_new_thread(project_id, assistant_name, thread_id)
            print("No existing thread. New thread created.")
        else:
            print("Thread ID updated successfully.")

    except Exception as e:
        print(f"An error occurred while updating the thread ID: {e}")
    finally:
        if conn:
            await conn.close()
