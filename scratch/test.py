import subprocess

# Define the command you want to run as a list
command = ["kobuddy",  "--errors", "return", "annotations"]

# Use subprocess.run to execute the command
# capture_output=True enables capturing the output
# text=True returns output as a string instead of bytes
result = subprocess.run(command, capture_output=True, text=True)

# Check if the command was successful
if result.returncode == 0:
    print("Command executed successfully!")
    print("Output:")
    print(result.stdout)
else:
    print("Command failed.")
    print("Error output:")
    print(result.stderr)
