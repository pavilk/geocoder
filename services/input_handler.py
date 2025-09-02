from services.geocoder import handle_address_input, handle_coordinates_input


async def handle_command(command: str):
    if command == "1":
        await handle_coordinates_input()
    elif command == "2":
        await handle_address_input()
    else:
        print("Неизвестная команда")
