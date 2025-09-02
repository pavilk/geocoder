import asyncio
import sys
from services.input_handler import handle_command
from database.models import init_db


async def main():
    await init_db()

    print("Добро пожаловать в GeoApp!")
    while True:
        print("\nВведите команду:")
        print("1 — Ввести координаты")
        print("2 — Ввести адрес")
        print("exit — Выход")

        command = input(">> ").strip().lower()
        if command == "exit":
            print("Выход.")
            break

        await handle_command(command)


if __name__ == "__main__":
    asyncio.run(main())
