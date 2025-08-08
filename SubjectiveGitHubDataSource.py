import os
import subprocess
import time
import requests
from subjective_abstract_data_source_package import SubjectiveDataSource
from brainboost_data_source_logger_package.BBLogger import BBLogger


class SubjectiveGitHubDataSource(SubjectiveDataSource):
    def __init__(self, name=None, session=None, dependency_data_sources=[], subscribers=None, params=None):
        super().__init__(name=name, session=session, dependency_data_sources=dependency_data_sources,
                         subscribers=subscribers, params=params)

    def fetch(self):
        start_time = time.time()
        username = self.params.get('username')
        token = self.params.get('token')
        target_directory = self.params.get('target_directory', '')
        BBLogger.log(f"Starting GitHub fetch for user '{username}' into '{target_directory}'.")

        if not os.path.exists(target_directory):
            try:
                os.makedirs(target_directory)
                BBLogger.log(f"Created directory {target_directory}")
            except OSError as e:
                BBLogger.log(f"Failed to create directory '{target_directory}': {e}", level="error")
                raise

        headers = {}
        if token:
            headers['Authorization'] = f"token {token}"
        repos_url = f"https://api.github.com/users/{username}/repos?per_page=100"
        response = requests.get(repos_url, headers=headers)
        if response.status_code != 200:
            BBLogger.log(f"Failed to fetch repositories: {response.status_code}", level="error")
            return

        repos = response.json()
        super().set_total_items(len(repos))
        BBLogger.log(f"Set total items to: {super().get_total_to_process()}")

        for repo in repos:
            repo_name = repo.get("name")
            clone_url = repo.get("clone_url")
            if not clone_url:
                BBLogger.log(f"Repository {repo_name} has no clone URL. Skipping.")
                continue

            step_start = time.time()
            dest_path = os.path.join(target_directory, repo_name)
            if os.path.exists(dest_path) and os.listdir(dest_path):
                BBLogger.log(f"Repository {repo_name} already exists. Skipping clone.")
            else:
                try:
                    BBLogger.log(f"Cloning repository {repo_name} from {clone_url} ...")
                    subprocess.run(["git", "clone", clone_url, dest_path],
                                   check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    BBLogger.log(f"Repository {repo_name} cloned successfully.")
                except subprocess.CalledProcessError as e:
                    BBLogger.log(f"Error cloning {repo_name}: {e.stderr.decode()}", level="error")
            elapsed = time.time() - step_start
            super().set_total_processing_time(super().get_total_processing_time() + elapsed)
            super().increment_processed_items()
            if self.progress_callback:
                est_time = self.estimated_remaining_time()
                self.progress_callback(self.get_name(),
                                       super().get_total_to_process(),
                                       super().get_total_processed(),
                                       est_time)
                BBLogger.log(f"Progress callback: {self.get_name()}, Total: {super().get_total_to_process()}, "
                             f"Processed: {super().get_total_processed()}, Estimated remaining time: {est_time:.2f} seconds")
        super().set_fetch_completed(True)
        BBLogger.log("GitHub fetch process completed.")

    def get_icon(self):
        icon_path = os.path.join(os.path.dirname(__file__), 'icon.svg')
        try:
            if os.path.exists(icon_path):
                with open(icon_path, 'r', encoding='utf-8') as f:
                    return f.read()
        except Exception:
            pass
        return """<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\"><path fill=\"#000\" d=\"M12 .5a12 12 0 0 0-3.793 23.39c.6.112.82-.26.82-.58 0-.286-.01-1.044-.016-2.05-3.338.726-4.042-1.61-4.042-1.61-.546-1.386-1.334-1.756-1.334-1.756-1.09-.744.083-.729.083-.729 1.206.084 1.84 1.238 1.84 1.238 1.072 1.836 2.813 1.306 3.498.999.108-.776.42-1.307.763-1.607-2.665-.303-5.466-1.332-5.466-5.93 0-1.31.468-2.381 1.236-3.22-.124-.303-.536-1.523.117-3.176 0 0 1.008-.322 3.3 1.23a11.5 11.5 0 0 1 6.006 0c2.29-1.552 3.297-1.23 3.297-1.23.655 1.653.243 2.873.12 3.176.77.839 1.235 1.91 1.235 3.22 0 4.61-2.805 5.625-5.478 5.922.431.372.816 1.103.816 2.222 0 1.604-.014 2.896-.014 3.292 0 .322.217.698.827.579A12 12 0 0 0 12 .5Z\"/></svg>"""

    def get_connection_data(self):
        return {
            "connection_type": "GitHub",
            "fields": ["username", "token", "target_directory"]
        }
