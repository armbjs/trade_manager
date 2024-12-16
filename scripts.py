import os
import re
import tomlkit
import json

import typing
import pytz
import datetime
import subprocess

import mypy


def patp():
    publish("PATCH")


def majp():
    publish("MAJOR")


def minp():
    publish("MINOR")


def bump_major_version() -> None:
    """
    하위 호환성이 없을 때 사용

    :return:
    """
    # MAJOR version when you make incompatible API changes
    _bump_version("major")


def bump_minor_version() -> None:
    """
    하위 호환성이 있고, 기능을 추가했을 때 사용

    :return:
    """
    # MINOR version when you add functionality in a backward compatible manner
    _bump_version("minor")


def bump_patch_version() -> None:
    """
    하위 호환성이 있고, 버그 픽스시 사용
    :return:
    """
    # PATCH version when you make backward compatible bug fixes
    _bump_version("patch")


def _bump_version(version_core_type: str = "minor") -> None:
    """
    "poetry run publish" command will run this function.
    Use this to publish to pypi or private pypi.

    * 특정 버전으로 패키지를 배포하고 나면, 그 버전의 내용은 절대 변경하지 말아야 한다. 변경분이 있다면 반드시 새로운 버전으로 배포하도록 한다.
    * Major version 0(0.y.z)은 초기 개발을 위해서 쓴다.
    * 초기 개발 시, 0.1.0 -> 0.2.0 -> 0.3.0 과 같이 Major version 은 0 으로 두고, Minor version 만 하나씩 올린다.
    https://semver.org/

    """
    if version_core_type not in ["major", "minor", "patch"]:
        raise Exception("version_core_type 값은 ['major', 'minor', 'patch'] 중 하나여야 합니다.")

    with open("pyproject.toml", mode="rt", encoding="utf-8") as f:
        pyproject_dict: Dict[str, Any] = tomlkit.load(f)

    bumping_version_result = os.popen(f"poetry version {version_core_type}").read()
    print(f"bumping version to: {bumping_version_result}")
    project_name = pyproject_dict["tool"]["poetry"]["name"]
    project_name_with_underscore = project_name.replace("-", "_")

    new_version: str = os.popen("poetry version --short").read().strip("\r\n")

    if os.path.exists(f"./{project_name_with_underscore}/version.json"):
        with open(
                f"./{project_name_with_underscore}/version.json", "rt", encoding="utf-8"
        ) as f:
            version_dict = json.loads(f.read())
    else:
        # ISO 8601: https://www.w3.org/TR/NOTE-datetime
        version_dict = {
            "package-name": project_name,
            "version": "",
            "full-revisionid": None,
            "dirty": None,
            "error": "",
            "date": None,
        }
    version_dict["package-name"] = project_name
    version_dict["version"] = new_version

    # '2023-10-03T01:13:05.356128+00:00'
    datetime_str_in_iso8601_format = pytz.utc.localize(
        datetime.datetime.utcnow()
    ).isoformat()
    version_dict["date"] = datetime_str_in_iso8601_format

    with open(
            f"./{project_name_with_underscore}/version.json", "wt", encoding="utf-8"
    ) as f:
        f.write(json.dumps(version_dict))


def publish(version_bump_type):
    """
    2024-04-02 15:44

    * publish 를 poetry run 을 통해서 바로 실행하지 않도록 한다.
    * version_bump_type parameter 값은 {"MAJOR", "MINOR", "PATCH"} 값을 가진다.
    * _bump_version 에서, version.json 값을 업데이트한다.
    * 먼저, version 을 bump 하고, 새 버전 값을 읽어서, __init__.py 를 업데이트한다.


    * publish 에서 __init__.py 파일 수정하지 않도록 수정. __init__.py 내용은 version.json 값을 version.py
    안의 함수를 이용해서 조회해오도록 하고 내용을 매번 변경하지 않도록 함.

    """
    print("os.getcwd()", os.getcwd())

    with open("pyproject.toml", mode="rt", encoding="utf-8") as fp:
        config = tomlkit.load(fp)
    print("config", config)

    current_version_str = config['tool']['poetry']['version']
    print("current_version_str", current_version_str)

    version_core_type = version_bump_type.lower()

    _bump_version(version_core_type)

    new_version: str = os.popen("poetry version --short").read().strip("\r\n")
    print("new_version", new_version)

    project_specific_config = config.get("tool", {}).get("current-project", {})

    poetry_publish_enabled = project_specific_config.get("poetry-publish-enabled", False)
    docker_enabled = project_specific_config.get("docker-enabled", False)
    workflow_enabled = project_specific_config.get("workflow-enabled", False)

    print(f"poetry_publish_enabled: {poetry_publish_enabled}")
    print(f"docker_enabled: {docker_enabled}")
    print(f"workflow_enabled: {workflow_enabled}")

    if poetry_publish_enabled:
        cmd_str = "poetry publish -r pdr --build"
        print(f"{cmd_str}")
        os.system(cmd_str)

    if docker_enabled:
        with open("./docker/Dockerfile", "rt") as f:
            original_dockerfile = f.read()

            replaced_dockerfile = re.sub(pattern=r"==([0-9]+.[0-9]+.[0-9]+)",
                                         string=original_dockerfile,
                                         repl=f"=={new_version}")

        with open("./docker/Dockerfile", "wt") as f:
            f.write(replaced_dockerfile)

        print("Dockerfile updated")

    if workflow_enabled:
        project_name = config['tool']['poetry']['name']
        workflow_file_name = f"{project_name}-docker-image-publish.yaml"

        workflow_file_path = f".github/workflows/{workflow_file_name}"
        if os.path.exists(workflow_file_path):
            with open(workflow_file_path, "rt") as f:
                original_file = f.read()

                replaced_file = re.sub(pattern=r":([0-9]+.[0-9]+.[0-9]+)",
                                       string=original_file,
                                       repl=f":{new_version}")

            with open(workflow_file_path, "wt") as f:
                f.write(replaced_file)

        workflow_file_path = f".github/not_used_workflows/{workflow_file_name}"
        if os.path.exists(workflow_file_path):
            with open(workflow_file_path, "rt") as f:
                original_file = f.read()

                replaced_file = re.sub(pattern=r":([0-9]+.[0-9]+.[0-9]+)",
                                       string=original_file,
                                       repl=f":{new_version}")

            with open(workflow_file_path, "wt") as f:
                f.write(replaced_file)
        print(f"{workflow_file_name} updated")


def check_all():
    check_process_result = mypy()
    if check_process_result.returncode != 0:
        print("Checking process has failed.")
        return

    check_process_result = lint()
    if check_process_result.returncode != 0:
        print("Checking process has failed.")
        return

    check_process_result = test()
    if check_process_result.returncode != 0:
        print("Checking process has failed.")
        return


def type_check():
    """
    "poetry run mypy" command will run this function.
    It will execute pylint
    """
    with open("pyproject.toml", mode="rt", encoding="utf-8") as fp:
        pyproject_dict: typing.Dict[str, typing.Any] = tomlkit.load(fp)

    # poetry new creates package directory name with "_"
    project_name = pyproject_dict["tool"]["poetry"]["name"].strip('"').replace("-", "_")

    return subprocess.run(
        ["mypy", "./tests", f"./{project_name}"], check=False
    )


def lint():
    """
    "poetry run lint" command will run this function.
    It will execute pylint
    """

    with open("pyproject.toml", mode="rt", encoding="utf-8") as fp:
        pyproject_dict: typing.Dict[str, typing.Any] = tomlkit.load(fp)

    # poetry new creates package directory name with "_"
    project_name = pyproject_dict["tool"]["poetry"]["name"].strip('"').replace("-", "_")

    return subprocess.run(
        ["pylint", f"./{project_name}/**/*.py", "./tests/**/*.py"], check=False
    )


def test():
    """
    "poetry run test" command will run this function.
    It will execute pytest
    """
    return subprocess.run(["pytest"], check=False)
