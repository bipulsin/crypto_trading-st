#!/usr/bin/env python3

def add_default_capital():
    """Add default_capital attribute to the __init__ method"""
    
    # Read the current file
    with open('strategy_st.py', 'r') as f:
        lines = f.readlines()
    
    # Find the line with trailing stop configuration
    for i, line in enumerate(lines):
        if 'self.trailing_stop_distance = 100' in line:
            # Insert default_capital after this line
            new_line = '        self.default_capital = float(os.environ.get(\'DEFAULT_CAPITAL\', \'1000.0\'))\n'
            lines.insert(i + 1, new_line)
            break
    
    # Write back to file
    with open('strategy_st.py', 'w') as f:
        f.writelines(lines)
    
    print("✅ Successfully added default_capital attribute")
    return True

if __name__ == "__main__":
    add_default_capital()
