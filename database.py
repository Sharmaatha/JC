import psycopg2
from psycopg2.extras import Json
from config import DB_CONFIG, CREATED_BY
from datetime import datetime

class Database:
    def __init__(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        """Auto-create required tables if they do not exist"""
        try:
            #  companies table
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                id SERIAL PRIMARY KEY,
                company_name TEXT UNIQUE,
                products TEXT[],
                product_id TEXT[],
                created_by TEXT,
                updated_by TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );
            """)

            #  products table 
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
                product_name TEXT,
                metadata JSONB,
                is_social_media BOOLEAN DEFAULT FALSE,
                twitter_link TEXT,
                linkedin_link TEXT,
                created_by TEXT,
                updated_by TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(company_id, product_name)
            );
            """)

            self.conn.commit()
            print("Tables checked/created")
        
        except Exception as e:
            self.conn.rollback()
            print(f"Error creating tables: {e}")
            raise

    def close(self):
        self.cursor.close()
        self.conn.close()

    def get_or_create_company(self, company_name):
        """Get existing company or create new one"""
        try:
            self.cursor.execute(
                "SELECT id FROM companies WHERE company_name = %s",
                (company_name,)
            )
            result = self.cursor.fetchone()
            
            if result:
                return result[0]

            self.cursor.execute(
                """
                INSERT INTO companies (company_name, created_by, updated_by)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (company_name, CREATED_BY, CREATED_BY)
            )

            company_id = self.cursor.fetchone()[0]
            self.conn.commit()
            return company_id
        
        except Exception as e:
            self.conn.rollback()
            print(f"Error getting/creating company: {e}")
            raise

    def insert_product(self, company_id, product_name, metadata, twitter_link=None, linkedin_link=None):
        """Insert product with metadata"""
        try:
            is_social_media = bool(twitter_link or linkedin_link)

            self.cursor.execute(
                """
                INSERT INTO products 
                (company_id, product_name, metadata, is_social_media, twitter_link, linkedin_link, created_by, updated_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (company_id, product_name) DO NOTHING
                RETURNING id
                """,
                (
                    company_id, product_name, Json(metadata), 
                    is_social_media, twitter_link, linkedin_link, 
                    CREATED_BY, CREATED_BY
                )
            )

            result = self.cursor.fetchone()
            if not result:
                print(f"Product '{product_name}' already exists, skipping...")
                self.cursor.execute(
                    "SELECT id FROM products WHERE company_id = %s AND product_name = %s",
                    (company_id, product_name)
                )
                product_id = self.cursor.fetchone()[0]
                return product_id

            product_id = result[0]

            self.cursor.execute(
                """
                UPDATE companies 
                SET products = array_append(COALESCE(products, ARRAY[]::TEXT[]), %s),
                    product_id = array_append(COALESCE(product_id, ARRAY[]::TEXT[]), %s),
                    updated_at = %s,
                    updated_by = %s
                WHERE id = %s
                """,
                (product_name, str(product_id), datetime.now(), CREATED_BY, company_id)
            )

            self.conn.commit()
            return product_id

        except Exception as e:
            self.conn.rollback()
            print(f"Error inserting product: {e}")
            raise