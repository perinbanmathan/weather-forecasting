import math
# 1. Tower of Hanoi

def tower_of_hanoi(n, source, auxiliary, destination):
    if n == 1:
        print(f"Move disk 1 from {source} to {destination}")
        return
    tower_of_hanoi(n - 1, source, destination, auxiliary)
    print(f"Move disk {n} from {source} to {destination}")
    tower_of_hanoi(n - 1, auxiliary, source, destination)


def run_tower_of_hanoi():
    n = int(input("Enter number of disks: "))
    print("Steps to solve Tower of Hanoi:")
    tower_of_hanoi(n, 'A', 'B', 'C')


# 2. Tic Tac Toe (2 Players)

def run_tic_tac_toe():
    board = [" " for _ in range(9)]

    def print_board():
        print()
        print(f"{board[0]} | {board[1]} | {board[2]}")
        print("--+---+--")
        print(f"{board[3]} | {board[4]} | {board[5]}")
        print("--+---+--")
        print(f"{board[6]} | {board[7]} | {board[8]}")
        print()

    def check_winner(player):
        wins = [
            [0, 1, 2], [3, 4, 5], [6, 7, 8],
            [0, 3, 6], [1, 4, 7], [2, 5, 8],
            [0, 4, 8], [2, 4, 6]
        ]
        return any(board[i] == board[j] == board[k] == player for i, j, k in wins)

    def is_draw():
        return " " not in board

    player = "X"
    while True:
        print_board()
        try:
            move = int(input(f"Player {player}, enter your move (1-9): ")) - 1
            if board[move] != " ":
                print("Spot already taken. Try again.")
                continue
            board[move] = player
        except (ValueError, IndexError):
            print("Invalid input. Enter 1-9.")
            continue

        if check_winner(player):
            print_board()
            print(f"🎉 Player {player} wins!")
            break
        elif is_draw():
            print_board()
            print("It's a draw!")
            break
        player = "O" if player == "X" else "X"

# 3. Area of Circle

def area_of_circle():
    try:
        r = float(input("Enter radius: "))
        area = math.pi * r * r
        print(f"Area of circle: {area:.2f}")
    except ValueError:
        print("Invalid radius.")


# 4. Calculator
def calculator():
    def add(x, y):
        return x + y

    def sub(x, y):
        return x - y

    def mul(x, y):
        return x * y

    def div(x, y):
        return "Error" if y == 0 else x / y

    print("Select operation:")
    print("1. Add\n2. Subtract\n3. Multiply\n4. Divide")
    try:
        choice = input("Enter choice (1/2/3/4): ")
        x = float(input("Enter first number: "))
        y = float(input("Enter second number: "))

        operations = {
            '1': add,
            '2': sub,
            '3': mul,
            '4': div
        }

        if choice in operations:
            result = operations[choice](x, y)
            print(f"Result: {result}")
        else:
            print("Invalid operation.")
    except ValueError:
        print("Invalid number.")


# Main Menu

def main():
    while True:
        print("\n--- Python Multi-Function Program ---")
        print("1. Tower of Hanoi")
        print("2. Tic Tac Toe")
        print("3. Area of Circle")
        print("4. Calculator")
        print("5. Exit")

        choice = input("Enter your choice (1-5): ")

        options = {
            '1': run_tower_of_hanoi,
            '2': run_tic_tac_toe,
            '3': area_of_circle,
            '4': calculator,
            '5': lambda: print("Exiting program. Goodbye!")
        }

        if choice == '5':
            options[choice]()
            break
        elif choice in options:
            options[choice]()
        else:
            print("Invalid choice. Please enter 1 to 5.")


# Run the program
main()
