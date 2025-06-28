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
        # Placeholder SVG icon for GitHub
        return """
        <svg viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
          <path fill="#000" d="M10 0C4.477 0 0 4.477 0 10c0 4.418 2.865 8.166 6.839 9.489.5.09.682-.217.682-.483 
          0-.237-.009-.868-.014-1.703-2.782.605-3.369-1.342-3.369-1.342-.454-1.159-1.11-1.468-1.11-1.468-.909-.621.07-.608.07-.608 
          1.003.07 1.531 1.03 1.531 1.03.892 1.528 2.341 1.087 2.91.832.09-.647.35-1.087.636-1.338-2.22-.253-4.555-1.11-4.555-4.947 
          0-1.092.39-1.987 1.03-2.688-.104-.253-.447-1.274.098-2.656 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0 1 10 4.844c.85.004 
          1.705.115 2.504.338 1.908-1.296 2.747-1.026 2.747-1.026.546 1.382.203 2.403.1 2.656.64.701 1.03 1.596 1.03 2.688 
          0 3.847-2.337 4.692-4.565 4.942.359.309.679.92.679 1.855 0 1.338-.012 2.421-.012 2.752 0 .268.18.579.688.481A10 
          10 0 0 0 20 10c0-5.523-4.477-10-10-10z"/>
        </svg>
        """

    def get_connection_data(self):
        return {
            "connection_type": "GitHub",
            "fields": ["username", "token", "target_directory"]
        }
