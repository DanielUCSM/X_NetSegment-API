from ipaddress import IPv4Network
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator


def parse_network(value):
    if not isinstance(value, str) or "/" not in value:
        raise ValueError("Use una red IPv4 en formato CIDR, por ejemplo 192.168.1.0/24.")
    address, prefix = value.split("/", 1)
    if not prefix.isascii() or not prefix.isdecimal():
        raise ValueError("El prefijo CIDR debe ser un numero entre 0 y 32.")
    try:
        return IPv4Network(f"{address}/{prefix}", strict=True)
    except ValueError as error:
        raise ValueError("Red IPv4 invalida o direccion con bits de host activos.") from error


Network = Annotated[IPv4Network, BeforeValidator(parse_network)]


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class FLSMRequest(InputModel):
    network: Network
    subnets_needed: int = Field(strict=True, ge=1, le=4096)


class Department(InputModel):
    name: str = Field(min_length=1, max_length=80)
    hosts_needed: int = Field(strict=True, ge=1, le=4294967294)


class VLSMRequest(InputModel):
    base_network: Network
    departments: list[Department] = Field(min_length=1, max_length=1024)

    @model_validator(mode="after")
    def unique_names(self):
        names = [department.name.casefold() for department in self.departments]
        if len(names) != len(set(names)):
            raise ValueError("Los nombres de los departamentos deben ser unicos.")
        return self


class AggregateRequest(InputModel):
    networks: list[Network] = Field(min_length=1, max_length=4096)
