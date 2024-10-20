
from flask import Flask, request, render_template, redirect, url_for
import sqlite3
import re

app = Flask(__name__)

# Define the Node class for AST
class Node:
    def __init__(self, node_type, value, left=None, right=None):
        self.node_type = node_type  # "operand" or "operator"
        self.value = value          # e.g., "age == 34" or "AND"
        self.left = left            # Left child (for AND/OR)
        self.right = right          # Right child (for AND/OR)

    def __repr__(self):
        # Check if the value is an integer or string and represent it accordingly
        if isinstance(self.value, int) or isinstance(self.value, float):
            print(f"Value (as number): {self.value}")
        elif isinstance(self.value, str):
            print(f"Value (as string): {self.value}")
        return f"Node(node_type={self.node_type}, value={self.value})"


# Database setup
def init_db():
    conn = sqlite3.connect('rule_engine.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_text TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Function to add a rule to the database
def add_rule_to_db(rule):
    conn = sqlite3.connect('rule_engine.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO rules (rule_text) VALUES (?)', (rule,))
    conn.commit()
    conn.close()

# Function to retrieve all rules from the database
def get_all_rules():
    conn = sqlite3.connect('rule_engine.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM rules')
    rules = cursor.fetchall()
    conn.close()
    return rules


# Function to parse and create AST
def create_rule(rule_string):
    """Parse a rule string and create an Abstract Syntax Tree (AST)."""
    def parse_expression(expr):
        # Adjusted regex to capture field names, operators, and values more accurately
        tokens = re.findall(r"[\w]+|[><=!]=?|'.?'|\".?\"|and|or|\(|\)", expr, re.IGNORECASE)
        # print(tokens)
        return tokens

    def build_ast(tokens):
        stack = []
        for token in tokens:
            if token.lower() == "and" or token.lower() == "or":
                right = stack.pop()
                left = stack.pop()
                node = Node("operator", token.lower(), left, right)
                stack.append(node)
            else:
                node = Node("operand", value=token)
                print(node)
                stack.append(node)
                # print(stack)
        return stack[0] if stack else None

    tokens = parse_expression(rule_string)
    print(f"Parsed Tokens: {tokens}")  # Debugging: Show parsed tokens
    root_node = build_ast(tokens)
    return root_node

def evaluate_rule(node, data):
    # Ensure field names in the data dictionary are treated consistently
    data = {k.lower(): v for k, v in data.items()}

    if node.node_type == "operand":
        # Enhanced regex to match comparison patterns more flexibly
        match = re.match(r"(?i)([a-zA-Z]+)\s*([><=!]=?)\s*(\d+|'.?'|\".?\")", node.value.strip())

        if match:
            field, operator, value = match.groups()

            # Convert field name to lowercase to match data
            field = field.lower()

            # Fetch the data value, ensuring case-insensitive matching
            data_value = data.get(field)
            if data_value is None:
                print(f"Field '{field}' not found in data.")
                return False

            # Parse value as integer if it is a digit, otherwise treat as a string
            if value.isdigit():
                value = int(value)
            else:
                # Strip quotes from strings
                value = value.strip("'").strip('"').lower()

            # Convert data values to lowercase for consistent string comparisons
            if isinstance(data_value, str):
                data_value = data_value.lower()

            # Debugging output for clear insights
            print(f"Evaluating: {field} {operator} {value} (data_value: {data_value})")

            # Perform the comparison
            if operator == ">":
                return data_value > value
            elif operator == "<":
                return data_value < value
            elif operator == "==":
                return data_value == value
            elif operator == "!=":
                return data_value != value
            elif operator == ">=":
                return data_value >= value
            elif operator == "<=":
                return data_value <= value

        # If the expression doesn't match, log it and return False
        print(f"Invalid match for node value: {node.value}")
        return False

    # Evaluate logical operators (AND, OR)
    if node.value.lower() == "and":
        return evaluate_rule(node.left, data) and evaluate_rule(node.right, data)
    if node.value.lower() == "or":
        return evaluate_rule(node.left, data) or evaluate_rule(node.right, data)

    # Log for unrecognized node types
    print(f"Unrecognized node type: {node.node_type} with value: {node.value}")
    return False





# Home route
@app.route('/')
def index():
    return render_template('index.html')

# Add Rule Page
@app.route('/add_rule', methods=['GET', 'POST'])
def add_rule():
    if request.method == 'POST':
        rule = request.form['rule']
        add_rule_to_db(rule)
        return redirect(url_for('index'))
    return render_template('add_rule.html')

# Evaluate Rule Page
@app.route('/eval', methods=['GET', 'POST'])
def evaluate():
    result = None
    if request.method == 'POST':
        rule_id = request.form['rule_id']
        user_data = {
            'age': int(request.form.get('age')),
            'department': request.form.get('department','').lower(),
            'salary': int(request.form.get('salary')),
            'experience': int(request.form.get('experience'))
        }
        conn = sqlite3.connect('rule_engine.db')
        cursor = conn.cursor()
        cursor.execute('SELECT rule_text FROM rules WHERE id = ?', (rule_id,))
        rule = cursor.fetchone()
        conn.close()

        if rule:
            rule_text = rule[0]
            rule_ast = create_rule(rule_text)
            result = evaluate_rule(rule_ast, user_data)
            print(result)

    rules = get_all_rules()
    return render_template('eval.html', result=result, rules=rules)

if __name__ == "__main__":
    init_db()  
    app.run(debug=False)