// See the file COPYRIGHT for copyright information.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

import * as ims from "./ims.ts";

declare let url_app: string;
declare let url_auth: string;

declare global {
    interface Window {
        login: ()=>void;
    }
}

//
// Initialize UI
//

initLoginPage();

async function initLoginPage(): Promise<void> {
    await ims.commonPageInit();
    document.getElementById("login_form")!.addEventListener("submit", (e: SubmitEvent): void => {
        e.preventDefault();
        login();
    });
    document.getElementById("username_input")?.focus();
}

async function login(): Promise<void> {
    const username = (document.getElementById("username_input") as HTMLInputElement).value;
    const password = (document.getElementById("password_input") as HTMLInputElement).value;
    const {json, err} = await ims.fetchJsonNoThrow<AuthResponse>(url_auth, {
        body: JSON.stringify({
            "identification": username,
            "password": password,
        }),
    });
    if (err != null || json == null) {
        ims.unhide(".if-authentication-failed");
        return;
    }
    ims.setAccessToken(json.token);
    const redirect = new URLSearchParams(window.location.search).get("o");
    if (redirect != null) {
        window.location.replace(redirect);
    } else {
        window.location.replace(url_app);
    }
}

type AuthResponse = {
    token: string;
}
