import numpy as np
import pandas as pd


class Classifier:
    """
    Classifier class to classify the text into right wing or pluralistic
    """

    def __init__(self, classifier_path):
        # load the hashtags
        self.hashtag_list = pd.read_csv(classifier_path + "hashtag_list_curated.csv")
        self.embeddings_right = np.load(classifier_path + "embeddings_right.npy")
        self.embeddings_pluralistic = np.load(classifier_path + "embeddings_pluralistic.npy")

    def _cosine_similarity(self, a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    def label_score(self, review_embedding, label_embeddings):
        return self._cosine_similarity(
            review_embedding, label_embeddings[0]
        ) - self._cosine_similarity(review_embedding, label_embeddings[1])

    def right_wing_classifier(self, text, embeddings_client):
        search_hashtags = [i[0] for i in np.array(self.hashtag_list)]

        def contains_word(s, l):
            return any(map(lambda x: x in s, l))

        if contains_word(text, ["#afdverbot", "fckafd"]):
            result = "pluralistic"

        elif contains_word(text, search_hashtags):
            result = "right"

        else:
            # try out the zero shot method via openAI embedding
            # right_class = [
            #     "Unter 'Rechtsextremismus' verstehen wir die Gesamtheit von Einstellungen, die von der rassisch oder ethnisch bedingten sozialen Ungleichheit der Menschen ausgehen, nach ethnischer Homogenität von Völkern verlangen und das Gleichheitsgebot der Menschenrechts-Deklaration ablehnen, die den Vorrang der Gemeinschaft vor dem Individuum betonen, von der Unterordnung des Bürgers unter die Staatsräson ausgehen und die den Wertepluralismus einer liberalen Demokratie ablehnen und Demokratisierung rückgängig machen wollen."
            # ]
            # pluralistic_view = [
            #     "Pluralismus (Politik) ist die friedliche Koexistenz von verschiedenen Interessen und Lebensstilen in einer Gesellschaft."
            # ]
            embeddings = embeddings_client.embed_documents([text])

            result = (
                "right"
                if self.label_score(
                    embeddings[0], [self.embeddings_right[0], self.embeddings_pluralistic[0]]
                )
                > 0
                else "pluralistic"
            )

        return result

    def right_wing_classifier_f_embeddings(self, array_text, embeddings, embeddings_client):
        search_hashtags = [i[0] for i in np.array(self.hashtag_list)]

        def contains_word(s, l):
            return any(map(lambda x: x in s, l))

        contains_hashtags = np.array([contains_word(text, search_hashtags) for text in array_text])
        contains_afdverbot = np.array(
            [contains_word(text, ["#afdverbot", "fckafd"]) for text in array_text]
        )

        remaining = np.logical_and(~contains_hashtags, ~contains_afdverbot)

        rem_embeddings = embeddings[remaining]

        results = np.empty_like(array_text, dtype=object)

        results[contains_hashtags] = "right"
        results[contains_afdverbot] = "pluralistic"

        result_rem = [
            (
                "right"
                if self.label_score(
                    rem_embeddings[i], [self.embeddings_right[0], self.embeddings_pluralistic[0]]
                )
                > 0
                else "pluralistic"
            )
            for i in range(len(rem_embeddings))
        ]

        results[remaining] = result_rem

        return results
