def parse_instructions(list_of_inst):
    instructions = []
    for instr in list_of_inst:
        instr = instr.strip()
        if not (instr == "" or instr[0:len(COMMENT_SYMBOL)] == COMMENT_SYMBOL):
            instructions.append(instr)
    print(instructions)
    return instructions


def get_command(instruction):
    """
    Gets the command from an instruction
    :param instruction: instruction for RFES
    :return: the command from the instruction
    """
    try:
        open_parenthesis_index = instruction.index("(")
        command = instruction[:open_parenthesis_index]
        return command
    except Exception as e:
        print("Can't find open parenthesis")


def get_value(instruction):
    """
    Gets the value from an instruction
    :param instruction: instruction for RFES
    :return: the value inside the parenthesis
    """
    try:
        open_parenthesis_index = instruction.index("(")
        value = instruction[open_parenthesis_index + 1:-1]
        return value
    except Exception as e:
        print("Can't find open parenthesis")


def check_commands(list_of_instructions):
    valid_instructions = []
    try:
        for instruction in list_of_instructions:
            command = get_command(instruction)
            value = get_value(instruction)
            if command not in COMMANDS_STRING.keys():
                raise Exception(command + " is an invalid command!")
            try:
                float(value)
            except Exception as e:
                raise Exception(value + " is not a valid value!")
            valid_instructions.append(command + " " + value)
        return valid_instructions
    except Exception as e:
        print(e)
        return []


def path_to_instructions(path):
    instructions_file = open(path, 'r')
    raw_instructions = instructions_file.readlines()
    parsed_instructions = parse_instructions(raw_instructions)  # results in ['forward(10)', 'left(90)', ...]
    checked_instructions = check_commands(parsed_instructions) # makes sure they are all valid
    return checked_instructions


def instruction_as_tuple(instruction):
    instr = instruction.split(" ")
    return instr[0], instr[1]

# this needs to match with RFES_Control_Center: [W, A, S, D, spacebar, up, down, left, right, m_y, m_x]
COMMANDS_STRING = {'forward': 0, 'left': 1, 'backward': 2, 'right': 3, 'spray': 4, 'aim_up': 5, 'aim_down': 6,
                   'aim_left': 7, 'aim_right': 8}

COMMENT_SYMBOL = "//"

# TEST - make sure to comment when done
instructions_file_path = 'instructions.txt'
list_of_inst = path_to_instructions(instructions_file_path)
print(list_of_inst)
print(instruction_as_tuple(list_of_inst[3]))
