"""
First-run setup: creates a company (tenant) and its first admin user in an empty database.

Run this once after pointing DATABASE_URL at a new PostgreSQL database:

    python create_admin.py

It asks for the company name, admin username and password.
You can also pass some of them as options:

    python create_admin.py --tenant "Acme Motors" --name admin

After that, log in to the website as that admin and create more users
(technicians, approvers) from the app or the /users API endpoint.
"""
import argparse
import getpass
import os
import sys

from passlib.context import CryptContext
from sqlmodel import Session, SQLModel, create_engine, select

from models import Tenant, User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def main():
    parser = argparse.ArgumentParser(description="Create the first company and admin user.")
    parser.add_argument("--tenant", help="Company / OEM name, for example 'Acme Motors'")
    parser.add_argument("--name", help="Admin username (used to log in)")
    parser.add_argument("--password", help="Admin password (leave out to be asked securely)")
    args = parser.parse_args()

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        sys.exit("DATABASE_URL is not set. See README.md for setup instructions.")

    tenant_name = (args.tenant or input("Company name: ")).strip()
    admin_name = (args.name or input("Admin username: ")).strip()
    password = args.password
    if not password:
        password = getpass.getpass("Admin password (8 to 72 characters): ")
        if password != getpass.getpass("Repeat password: "):
            sys.exit("Passwords did not match. Nothing was created.")

    if not tenant_name or not admin_name:
        sys.exit("Company name and admin username cannot be empty. Nothing was created.")
    if len(password) < 8 or len(password.encode("utf-8")) > 72:
        sys.exit("Password must be 8 to 72 characters. Nothing was created.")

    engine = create_engine(database_url)
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        # Login looks users up by name only, so a name can only be used once
        if session.exec(select(User).where(User.name == admin_name)).first():
            sys.exit(f"A user named '{admin_name}' already exists. Nothing was created.")

        tenant = session.exec(select(Tenant).where(Tenant.name == tenant_name)).first()
        if not tenant:
            tenant = Tenant(name=tenant_name)
            session.add(tenant)
            session.commit()
            session.refresh(tenant)

        user = User(
            name=admin_name,
            role="admin",
            password=pwd_context.hash(password),
            tenant_id=tenant.id,
        )
        session.add(user)
        session.commit()

    print(f"Done. Company '{tenant_name}' is ready and '{admin_name}' can now log in as an admin.")


if __name__ == "__main__":
    main()