#!/usr/bin/env python3

def replace_wallet_method():
    """Replace the get_wallet_balance method with error handling version"""
    
    # Read the current file
    with open('strategy_st.py', 'r') as f:
        lines = f.readlines()
    
    # Find the start and end of the get_wallet_balance method
    start_line = None
    end_line = None
    
    for i, line in enumerate(lines):
        if 'def get_wallet_balance(self) -> float:' in line:
            start_line = i
        elif start_line is not None and line.strip() == '':
            end_line = i
            break
    
    if start_line is None:
        print("❌ Could not find get_wallet_balance method")
        return False
    
    if end_line is None:
        end_line = start_line + 3  # Assume it's just 3 lines
    
    # Read the patch content
    with open('wallet_balance_patch.txt', 'r') as f:
        patch_lines = f.readlines()
    
    # Replace the method
    new_lines = lines[:start_line] + patch_lines + lines[end_line:]
    
    # Write back to file
    with open('strategy_st.py', 'w') as f:
        f.writelines(new_lines)
    
    print("✅ Successfully replaced get_wallet_balance method")
    return True

if __name__ == "__main__":
    replace_wallet_method()
