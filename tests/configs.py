import os
import sys
import dotenv

current_module = sys.modules[__name__]

dotenv_path = os.path.join(
    os.path.dirname(__file__), '../.env'
)
print("dotenv_path", dotenv_path)
dotenv.load_dotenv(dotenv_path=dotenv_path, override=True)

key_dict = {}

environment_variable_key_list = [
    "TIMEZONE",
    "ANTHROPIC_API_KEY"
]

for this_env_key in environment_variable_key_list:
    if this_env_key in os.environ:
        print(this_env_key, os.environ[this_env_key])
        key_dict[this_env_key] = os.environ[this_env_key]
    else:
        raise KeyError(f"ENV VAR 중 {this_env_key} 가 존재하지 않습니다.")

for this_env_key in environment_variable_key_list:
    setattr(current_module, this_env_key, key_dict[this_env_key])
