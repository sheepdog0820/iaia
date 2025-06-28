#!/usr/bin/env python
"""
UIの機能テスト（Seleniumなしでも実行可能）
レスポンシブ、JavaScript機能、フォーム送信などのテスト
"""

import requests
import json
import time
from urllib.parse import urljoin


class UIFunctionalityTester:
    """UI機能のテストクラス"""
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
    
    def log_result(self, test_name, status, message=""):
        """テスト結果をログに記録"""
        self.test_results.append({
            "test": test_name,
            "status": status,
            "message": message
        })
        status_symbol = "✓" if status == "PASS" else "✗" if status == "FAIL" else "⚠"
        print(f"{status_symbol} {test_name}: {message}")
    
    def test_page_accessibility(self):
        """基本ページのアクセシビリティテスト"""
        pages = [
            ("/", "ホームページ"),
            ("/accounts/login/", "ログインページ"),
            ("/accounts/demo/", "デモページ"),
            ("/accounts/signup/", "サインアップページ")
        ]
        
        for path, name in pages:
            try:
                response = self.session.get(urljoin(self.base_url, path))
                if response.status_code == 200:
                    self.log_result(f"{name}アクセス", "PASS", f"Status: {response.status_code}")
                else:
                    self.log_result(f"{name}アクセス", "FAIL", f"Status: {response.status_code}")
            except Exception as e:
                self.log_result(f"{name}アクセス", "FAIL", f"Error: {e}")
    
    def test_static_files(self):
        """静的ファイルの読み込みテスト"""
        static_files = [
            ("/static/css/arkham.css", "CSS"),
            ("/static/js/arkham.js", "JavaScript")
        ]
        
        for path, file_type in static_files:
            try:
                response = self.session.get(urljoin(self.base_url, path))
                if response.status_code == 200:
                    size = len(response.content)
                    self.log_result(f"{file_type}ファイル", "PASS", f"Size: {size} bytes")
                else:
                    self.log_result(f"{file_type}ファイル", "FAIL", f"Status: {response.status_code}")
            except Exception as e:
                self.log_result(f"{file_type}ファイル", "FAIL", f"Error: {e}")
    
    def test_responsive_content(self):
        """レスポンシブデザインの内容チェック"""
        try:
            response = self.session.get(self.base_url)
            content = response.text
            
            # Bootstrap/レスポンシブ要素の確認
            responsive_elements = [
                "navbar-toggler",
                "navbar-collapse",
                "container-fluid",
                "col-md-",
                "col-lg-"
            ]
            
            found_elements = []
            for element in responsive_elements:
                if element in content:
                    found_elements.append(element)
            
            if len(found_elements) >= 3:
                self.log_result("レスポンシブデザイン", "PASS", f"要素数: {len(found_elements)}")
            else:
                self.log_result("レスポンシブデザイン", "WARN", f"要素数が少ない: {len(found_elements)}")
                
        except Exception as e:
            self.log_result("レスポンシブデザイン", "FAIL", f"Error: {e}")
    
    def test_form_elements(self):
        """フォーム要素の存在確認"""
        pages_with_forms = [
            ("/accounts/login/", "ログインフォーム"),
            ("/accounts/demo/", "デモフォーム")
        ]
        
        for path, form_name in pages_with_forms:
            try:
                response = self.session.get(urljoin(self.base_url, path))
                content = response.text
                
                # フォーム要素の確認
                form_elements = ["<form", "csrf", "button", "input"]
                found_elements = sum(1 for element in form_elements if element in content)
                
                if found_elements >= 3:
                    self.log_result(f"{form_name}要素", "PASS", f"要素数: {found_elements}")
                else:
                    self.log_result(f"{form_name}要素", "WARN", f"要素数が少ない: {found_elements}")
                    
            except Exception as e:
                self.log_result(f"{form_name}要素", "FAIL", f"Error: {e}")
    
    def test_javascript_functionality(self):
        """JavaScript機能の基本チェック"""
        try:
            response = self.session.get(urljoin(self.base_url, "/static/js/arkham.js"))
            if response.status_code == 200:
                js_content = response.text
                
                # JavaScript機能の確認
                js_features = [
                    "function",
                    "addEventListener",
                    "fetch",
                    "querySelector",
                    "CSRF"
                ]
                
                found_features = sum(1 for feature in js_features if feature in js_content)
                
                if found_features >= 3:
                    self.log_result("JavaScript機能", "PASS", f"機能数: {found_features}")
                else:
                    self.log_result("JavaScript機能", "WARN", f"機能数が少ない: {found_features}")
            else:
                self.log_result("JavaScript機能", "FAIL", "JSファイルが読み込めません")
                
        except Exception as e:
            self.log_result("JavaScript機能", "FAIL", f"Error: {e}")
    
    def test_authentication_flow(self):
        """認証フローの基本テスト"""
        try:
            # デモログインの実行
            demo_response = self.session.get(urljoin(self.base_url, "/accounts/mock-social/google/"))
            
            if demo_response.status_code in [200, 302]:
                # ダッシュボードアクセスの確認
                dashboard_response = self.session.get(urljoin(self.base_url, "/accounts/dashboard/"))
                
                if dashboard_response.status_code == 200 and "ダッシュボード" in dashboard_response.text:
                    self.log_result("認証フロー", "PASS", "デモログイン成功")
                else:
                    self.log_result("認証フロー", "FAIL", "ダッシュボードアクセス失敗")
            else:
                self.log_result("認証フロー", "FAIL", f"デモログイン失敗: {demo_response.status_code}")
                
        except Exception as e:
            self.log_result("認証フロー", "FAIL", f"Error: {e}")
    
    def test_api_integration(self):
        """API統合の基本テスト"""
        try:
            # まず認証
            self.session.get(urljoin(self.base_url, "/accounts/mock-social/google/"))
            
            # APIエンドポイントのテスト
            api_endpoints = [
                ("/api/schedules/sessions/view/", "セッション一覧API"),
                ("/api/scenarios/history/?limit=5", "シナリオ履歴API")
            ]
            
            for path, api_name in api_endpoints:
                response = self.session.get(urljoin(self.base_url, path))
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        self.log_result(f"{api_name}", "PASS", f"JSON応答成功")
                    except json.JSONDecodeError:
                        self.log_result(f"{api_name}", "WARN", "JSON以外の応答")
                else:
                    self.log_result(f"{api_name}", "FAIL", f"Status: {response.status_code}")
                    
        except Exception as e:
            self.log_result("API統合", "FAIL", f"Error: {e}")
    
    def test_error_handling(self):
        """エラーハンドリングのテスト"""
        error_urls = [
            "/nonexistent-page/",
            "/accounts/invalid-endpoint/",
            "/api/invalid-api/"
        ]
        
        for url in error_urls:
            try:
                response = self.session.get(urljoin(self.base_url, url))
                if response.status_code == 404:
                    self.log_result("404エラー処理", "PASS", f"適切な404応答")
                elif response.status_code in [400, 403, 500]:
                    self.log_result("エラー処理", "PASS", f"Status: {response.status_code}")
                else:
                    self.log_result("エラー処理", "WARN", f"予期しないStatus: {response.status_code}")
            except Exception as e:
                self.log_result("エラー処理", "FAIL", f"Error: {e}")
    
    def test_security_headers(self):
        """セキュリティヘッダーの確認"""
        try:
            response = self.session.get(self.base_url)
            headers = response.headers
            
            # 重要なセキュリティヘッダー
            security_headers = [
                "X-Frame-Options",
                "X-Content-Type-Options",
                "Content-Security-Policy"
            ]
            
            found_headers = sum(1 for header in security_headers if header in headers)
            
            if found_headers >= 1:
                self.log_result("セキュリティヘッダー", "PASS", f"ヘッダー数: {found_headers}")
            else:
                self.log_result("セキュリティヘッダー", "WARN", "セキュリティヘッダーが少ない")
                
        except Exception as e:
            self.log_result("セキュリティヘッダー", "FAIL", f"Error: {e}")
    
    def run_all_tests(self):
        """全テストの実行"""
        print("=" * 60)
        print("UI機能テスト開始")
        print("=" * 60)
        
        tests = [
            self.test_page_accessibility,
            self.test_static_files,
            self.test_responsive_content,
            self.test_form_elements,
            self.test_javascript_functionality,
            self.test_authentication_flow,
            self.test_api_integration,
            self.test_error_handling,
            self.test_security_headers
        ]
        
        for test in tests:
            test()
            time.sleep(0.5)  # レート制限対策
        
        print("\n" + "=" * 60)
        print("テスト結果サマリー")
        print("=" * 60)
        
        pass_count = sum(1 for result in self.test_results if result["status"] == "PASS")
        fail_count = sum(1 for result in self.test_results if result["status"] == "FAIL")
        warn_count = sum(1 for result in self.test_results if result["status"] == "WARN")
        total_count = len(self.test_results)
        
        print(f"合計テスト数: {total_count}")
        print(f"成功: {pass_count}")
        print(f"失敗: {fail_count}")
        print(f"警告: {warn_count}")
        
        if fail_count == 0:
            print("\n✓ 全てのテストが成功しました！")
            return True
        else:
            print(f"\n✗ {fail_count}個のテストが失敗しました")
            return False


if __name__ == "__main__":
    # サーバー動作確認
    try:
        response = requests.get("http://localhost:8000", timeout=5)
        if response.status_code != 200:
            print(f"⚠ サーバーレスポンス異常: {response.status_code}")
    except requests.exceptions.RequestException:
        print("❌ サーバーが動作していません")
        print("./server.sh start でサーバーを起動してください")
        exit(1)
    
    # テスト実行
    tester = UIFunctionalityTester()
    success = tester.run_all_tests()
    
    exit(0 if success else 1)