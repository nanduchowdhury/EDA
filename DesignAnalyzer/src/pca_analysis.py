import pandas as pd
import numpy as np

from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
try:
    import umap
except ImportError:
    umap = None


from sklearn.cluster import KMeans


class DimensionalityReducer:
    def __init__(self, df: pd.DataFrame, columns: list):
        self.df = df.copy()
        self.columns = columns
        self._validate_columns()
        self.data = self.df[self.columns].values
        self.pca_result = None
        self.tsne_result = None
        self.umap_result = None


    def _validate_columns(self):
        """Validate that the selected columns can be used for analysis."""
        # Check columns exist
        missing_cols = [col for col in self.columns if col not in self.df.columns]
        if missing_cols:
            raise ValueError(f"Columns not found in DataFrame: {missing_cols}")

        # Check all numeric
        non_numeric_cols = [
            col for col in self.columns
            if not np.issubdtype(self.df[col].dtype, np.number)
        ]
        if non_numeric_cols:
            raise ValueError(f"Non-numeric columns cannot be analyzed: {non_numeric_cols}")

        # Check no NaN
        if self.df[self.columns].isnull().any().any():
            raise ValueError("Data contains NaN values. Please clean before analysis.")


    def run_pca(self, n_components=2):
        try:
            pca = PCA(n_components=n_components)
            self.pca_result = pca.fit_transform(self.data)
            return pd.DataFrame(self.pca_result, columns=[f"PCA{i+1}" for i in range(n_components)])
        except Exception as e:
            raise RuntimeError(f"PCA failed: {e}")

    def run_tsne(self, n_components=2, perplexity=30, random_state=42):
        try:
            tsne = TSNE(n_components=n_components, perplexity=perplexity, random_state=random_state)
            self.tsne_result = tsne.fit_transform(self.data)
            return pd.DataFrame(self.tsne_result, columns=[f"tSNE{i+1}" for i in range(n_components)])
        except Exception as e:
            raise RuntimeError(f"t-SNE failed: {e}")

    def run_umap(self, n_components=2, n_neighbors=15, min_dist=0.1, random_state=42):
        if umap is None:
            raise ImportError("UMAP is not installed. Please install with 'pip install umap-learn'.")
        try:
            reducer = umap.UMAP(n_components=n_components, n_neighbors=n_neighbors, 
                            min_dist=min_dist, random_state=random_state)
            self.umap_result = reducer.fit_transform(self.data)
            return pd.DataFrame(self.umap_result, columns=[f"UMAP{i+1}" for i in range(n_components)])
        except Exception as e:
            raise RuntimeError(f"UMAP failed: {e}")

    def get_pca_output(self):
        if self.pca_result is None:
            raise ValueError("PCA has not been run yet.")
        return pd.DataFrame(self.pca_result, columns=[f"PCA{i+1}" for i in range(self.pca_result.shape[1])])

    def get_tsne_output(self):
        if self.tsne_result is None:
            raise ValueError("t-SNE has not been run yet.")
        return pd.DataFrame(self.tsne_result, columns=[f"tSNE{i+1}" for i in range(self.tsne_result.shape[1])])

    def get_umap_output(self):
        if self.umap_result is None:
            raise ValueError("UMAP has not been run yet.")
        return pd.DataFrame(self.umap_result, columns=[f"UMAP{i+1}" for i in range(self.umap_result.shape[1])])
    




class KMeansClusterer:
    def __init__(self, df: pd.DataFrame, columns: list):
        self.df = df.copy()
        self.columns = columns
        self._validate_columns()
        self.data = self.df[self.columns].values
        self.kmeans_result = None

    def _validate_columns(self):
        missing_cols = [col for col in self.columns if col not in self.df.columns]
        if missing_cols:
            raise ValueError(f"Columns not found in DataFrame: {missing_cols}")
        non_numeric_cols = [
            col for col in self.columns
            if not np.issubdtype(self.df[col].dtype, np.number)
        ]
        if non_numeric_cols:
            raise ValueError(f"Non-numeric columns cannot be clustered: {non_numeric_cols}")
        if self.df[self.columns].isnull().any().any():
            raise ValueError("Data contains NaN values. Please clean before clustering.")
        

    def run_kmeans(self, n_clusters=3, random_state=42):
        try:
            kmeans = KMeans(n_clusters=n_clusters, random_state=random_state)
            labels = kmeans.fit_predict(self.data)
            self.kmeans_result = labels
            # Return a dataframe with original data and cluster labels
            result_df = self.df.copy()
            result_df['Cluster'] = labels
            return result_df
        except Exception as e:
            raise RuntimeError(f"KMeans clustering failed: {e}")

    def assign_cluster_colors(self, df):
        """
        Assigns a color to each unique integer value in the 'Cluster' column of df.
        Returns a new DataFrame with a 'Color' column.
        """

        if 'Cluster' not in df.columns:
            raise ValueError("No 'Cluster' column found to assign colors.")

        # Define a color palette (expand as needed)
        color_palette = [
            "blue", "orange", "green", "red", "purple",
            "brown", "pink", "gray", "yellow", "cyan"
        ]

        clusters = sorted(df['Cluster'].unique())
        color_map = {cluster: color_palette[i % len(color_palette)] for i, cluster in enumerate(clusters)}
        df = df.copy()
        df['Color'] = df['Cluster'].map(color_map)

        return df

    def get_cluster_labels(self):
        if self.kmeans_result is None:
            raise ValueError("KMeans has not been run yet.")
        return self.kmeans_result
    

