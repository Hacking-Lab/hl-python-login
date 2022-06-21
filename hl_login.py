#!/usr/bin/env python3

import argparse
import requests
import configparser
import sys
import logging as log
import time
from datetime import datetime
from datetime import timedelta
from requests.models import Response
from typing import Dict


parser = argparse.ArgumentParser(description="Hacking-Lab Login")

config = configparser.ConfigParser()

if config.read('config'):
    # if config file is being used
    try:
        defaultLogin = config['DEFAULT']['defaultLogin']
    except:
        print("ERROR: defaultLogin not configured in default section")
        sys.exit(1)

    if config.has_section(defaultLogin):
        try:
            tenant = config[defaultLogin]['tenant']
            username = config[defaultLogin]['username']
            password = config[defaultLogin]['password']
        except:
            print("ERROR: tenant, username or password not available in config file")
            sys.exit(1)


    else:
        print("ERROR: tenant configured in defaultSection is not available in config file")
        sys.exit(1)
else:
    # if no config file is used; ask the user for the info from the command line
    parser.add_argument('--tenant', type=str, help="the tenant for the login (ost, hslu, compass)", required=True)
    parser.add_argument('--username', type=str, help="the username for the login", required=True)
    parser.add_argument('--password', type=str, help="the password for the login", required=True)
    args = parser.parse_args()
    tenant = args.tenant
    username = args.username
    password = args.password
    


class AuthorizedSession:
    def __init__(self, tenant: str, username: str, password: str) -> None:
        self.tenant = tenant
        self.username = username
        self.password = password
        self._reset_tokens()


    def get(self, path: str) -> Response:
        self._ensure_login()
        url = f"https://{self.tenant}.hacking-lab.com/{path}"
        response = requests.get(
            url, headers={"Authorization": f"Bearer {self._access_token}"}
        )
        return response

    def logout(self) -> bool:
        log.info("logout")
        try:
            logout_request = requests.post(
                f"https://auth.{self.tenant}-dc.hacking-lab.com/auth/realms/{self.tenant}/protocol/openid-connect/logout/",
                data={
                    "client_id": "ccs",
                    "refresh_token": self._refresh_token,
                },
            )
            logout_request.raise_for_status()
            self._reset_tokens()
        except requests.exceptions.HTTPError:
            return False
        return True

    def _reset_tokens(self) -> None:
        self._access_token = None
        self._refresh_token = None
        self._access_expires_at = datetime.now() - timedelta(weeks=1)
        self._refresh_expires_at = datetime.now() - timedelta(weeks=1)

    def _authorize(self) -> bool:
        log.info("_authorize")
        return self._token(
            {
                "username": self.username,
                "password": self.password,
                "grant_type": "password",
                "client_id": "ccs",
            }
        )

    def _refresh(self) -> None:
        log.info("_refresh")
        return self._token(
            {
                "grant_type": "refresh_token",
                "client_id": "ccs",
                "refresh_token": self._refresh_token,
            }
        )

    # {self.tenant}
    def _token(self, data: Dict) -> bool:
        # print(f"login: https://auth.ost-dc.hacking-lab.com/auth/realms/{self.tenant}/protocol/openid-connect/token/")
        # print("_token", data)
        try:
            token_request = requests.post(
                f"https://auth.ost-dc.hacking-lab.com/auth/realms/{self.tenant}/protocol/openid-connect/token/",
                data=data,
            )
            # print(token_request.text)
            token_request.raise_for_status()
            token_json = token_request.json()
            self._access_token = token_json["access_token"]
            self._refresh_token = token_json["refresh_token"]
            self._access_expires_at = datetime.now() + timedelta(
                seconds=token_json["expires_in"]
            )
            self._refresh_expires_at = datetime.now() + timedelta(
                seconds=token_json["refresh_expires_in"]
            )
        except requests.exceptions.HTTPError:
            # print("request error")
            return False
        return True

    def _ensure_login(self) -> bool:
        if datetime.now() >= self._refresh_expires_at:
            log.info("refresh token expired")
            return self._authorize()
        elif datetime.now() >= self._access_expires_at:
            print("must refresh")
            log.info("access token expired")
            return self._refresh()

    def __enter__(self):
        print("__enter__")
        self._ensure_login()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        print("__exit__")
        self.logout()


def getProfile(authorized_session):
    
    result = authorized_session.get(f'api/user/profile')
    
    if result.status_code == 200:
        print("SUCCESS", result.status_code)
        return result.json()
    else:
        print("ERROR: invalid username or password", result.status_code)
        

authorized_session = AuthorizedSession(tenant, username, password)
result = getProfile(authorized_session)


