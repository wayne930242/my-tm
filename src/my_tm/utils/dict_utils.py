import re
from typing import Dict
import inflect
from my_tm.config.logger import logger

# Initialize the inflect engine
p = inflect.engine()

# Global set to track terms that have been seen
global_seen_terms = set()


def safe_singular_noun(phrase: str) -> str:
    if not phrase.strip():
        return phrase

    words = phrase.split()
    if len(words) > 1:
        last_word = words[-1]
        try:
            singular_last = p.singular_noun(last_word)
            if singular_last and not isinstance(singular_last, bool):
                words[-1] = singular_last
            return " ".join(words)
        except Exception as e:
            logger.warning(
                f"Error getting singular form for last word in '{phrase}': {str(e)}"
            )
            return phrase
    else:
        try:
            singular = p.singular_noun(phrase)
            if isinstance(singular, bool):
                return phrase
            return singular if singular else phrase
        except Exception as e:
            logger.warning(f"Error getting singular form for '{phrase}': {str(e)}")
            return phrase


def create_case_insensitive_dict(term_dict: Dict[str, str]) -> Dict[str, tuple]:
    result = {}
    for k, v in term_dict.items():
        if not k.strip():
            logger.warning("Encountered an empty key in term_dict. Skipping.")
            continue
        lower_k = k.lower()
        result[lower_k] = (k, v)
        # Add singular form if it's different
        singular = safe_singular_noun(lower_k)
        if singular and singular != lower_k:
            result[singular] = (k, v)
    return result


def simple_term_replacement(text: str, term_dict: Dict[str, str]) -> str:
    """
    Replaces specific terms in the text based on the provided dictionary.

    - The first occurrence of a term is displayed as `[[[Translation (Original Term)]]]`
    - Subsequent occurrences are displayed as `[[[Translation]]]`
    - Terms without a translation are left unchanged, and a warning is logged once

    :param text: The original text.
    :param term_dict: A dictionary of terms to be replaced, where keys are terms and values are their translations.
    :return: The text after term replacement.
    """
    if not text:
        # If the text is empty, return it as is
        return text

    if not term_dict:
        logger.debug("term_dict is empty. No replacements will be made.")
        return text

    case_insensitive_dict = create_case_insensitive_dict(term_dict)
    if not case_insensitive_dict:
        logger.debug(
            "Processed term dictionary is empty after filtering. No replacements will be made."
        )
        return text

    # Sort the dictionary keys by length in descending order to prevent partial matches
    sorted_terms = sorted(case_insensitive_dict.keys(), key=lambda x: (-len(x), x))
    # Create a regular expression pattern to match the terms, allowing for optional plural 's'
    pattern = re.compile(
        r"\b(" + "|".join(map(re.escape, sorted_terms)) + r")s?\b", re.IGNORECASE
    )
    replacement_count = 0
    local_seen_terms = set()

    def replace(match):
        nonlocal replacement_count
        matched = match.group(0)
        try:
            # Use the lowercase version of the matched term for lookup
            lookup_key = matched.lower()
            singular = safe_singular_noun(lookup_key)
            if singular != lookup_key:
                lookup_key = singular
            lookup_result = case_insensitive_dict.get(lookup_key)
            if lookup_result is None:
                # If no translation is found, log a warning once and return the original term
                if lookup_key not in replace.not_found:
                    logger.warning(
                        f"No translation found for '{matched}' (lookup key: '{lookup_key}')"
                    )
                    replace.not_found.add(lookup_key)
                return matched
            original_term, translation = lookup_result
            # Preserve the original casing if it matches exactly; otherwise, use the term's original case
            display_term = (
                matched if matched.lower() == original_term.lower() else original_term
            )

            # Check if this is the first occurrence of the term
            if (
                lookup_key not in global_seen_terms
                and lookup_key not in local_seen_terms
            ):
                result = f"[[[{translation} ({display_term})]]]"
                global_seen_terms.add(lookup_key)
                local_seen_terms.add(lookup_key)
            else:
                result = f"[[[{translation}]]]"

            replacement_count += 1
            return result
        except Exception as e:
            logger.error(f"Error processing term '{matched}': {str(e)}")
            return matched  # Return the original term if an error occurs

    # Initialize a set to track terms without translations
    replace.not_found = set()

    try:
        result = pattern.sub(replace, text)
        logger.debug(f"Found and replaced {replacement_count} terms")
        return result
    except Exception as e:
        logger.error(f"Error during term replacement: {str(e)}")
        return text  # Return the original text if an error occurs
