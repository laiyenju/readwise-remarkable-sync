"""
取得 Google OAuth2 refresh token，用於 GitHub Actions 認證。

用法：
  pip install google-auth-oauthlib
  python get_token.py <從 Google Cloud Console 下載的 OAuth client JSON 路徑>

執行後瀏覽器會自動開啟授權頁面，完成後終端會顯示 GOOGLE_OAUTH_CREDENTIALS 的值。
複製整段 JSON，貼到 GitHub Secrets 的 GOOGLE_OAUTH_CREDENTIALS 欄位。
"""

import json
import sys
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/drive']


def main():
    if len(sys.argv) < 2:
        print("用法：python get_token.py <oauth_client.json 路徑>")
        print("範例：python get_token.py ~/Downloads/client_secret_xxx.json")
        sys.exit(1)

    client_secrets_file = sys.argv[1]

    flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, SCOPES)
    creds = flow.run_local_server(port=0)

    output = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes)
    }

    print("\n✅ 授權成功！請複製以下內容，貼到 GitHub Secret GOOGLE_OAUTH_CREDENTIALS：\n")
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
