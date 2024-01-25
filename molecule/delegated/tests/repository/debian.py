import pytest

from ..util.util import (
    get_ansible,
    get_variable,
    get_from_url,
    get_os_role_variable,
    jinja_replacement,
)

testinfra_runner, testinfra_hosts = get_ansible()


def check_ansible_os_family(host):
    if get_variable(host, "ansible_os_family", True) != "Debian":
        pytest.skip("ansible_os_family mismatch")


def test_99osism(host):
    check_ansible_os_family(host)

    f = host.file("/etc/apt/apt.conf.d/99osism")
    assert f.exists
    assert f.mode == 0o644


def test_keys(host):
    check_ansible_os_family(host)

    repository_keys = get_variable(host, "repository_keys")

    for i in range(len(repository_keys)):
        content = get_from_url(repository_keys[i])

        f = host.file(f"/etc/apt/trusted.gpg.d/repository-{i}.asc")
        assert f.exists
        assert f.user == "root"
        assert f.group == "root"
        assert f.mode == 0o644

        assert content == f.content_string


def test_keydir(host):
    check_ansible_os_family(host)

    key_dir = get_variable(host, "repository_key_files_directory")

    if key_dir == "":
        pytest.skip("key_dir is empty")

    d = host.file(key_dir)
    assert d.exists
    assert d.is_directory

    key_count = 0
    for key_file in d.listdir():
        if not key_file.endswith(".gpg"):
            continue

        key_count += 1

    for i in range(key_count):
        f = host.file(f"/etc/apt/trusted.gpg.d/{i}.asc")
        assert f.exists
        assert f.user == "root"
        assert f.group == "root"
        assert f.mode == 0o644


def test_sources(host):
    check_ansible_os_family(host)

    f = host.file("/etc/apt/sources.list")
    assert f.exists
    assert f.user == "root"
    assert f.group == "root"
    assert f.mode == 0o644
    assert "DO NOT EDIT THIS FILE BY HAND" in f.content_string

    repositories = get_variable(host, "repository_dictionary")

    if len(repositories) <= 0:
        repositories = get_os_role_variable(host, "repository_default", "Ubuntu.yml")

    assert len(repositories) > 0

    for repository in repositories:
        ansible_distribution_release = get_variable(
            host, "ansible_distribution_release", True
        )
        repository["name"] = jinja_replacement(
            repository["name"],
            {"ansible_distribution_release": ansible_distribution_release},
        )
        repository["repository"] = jinja_replacement(
            repository["repository"],
            {"ansible_distribution_release": ansible_distribution_release},
        )

        assert repository["name"] in f.content_string
        assert repository["repository"] in f.content_string
