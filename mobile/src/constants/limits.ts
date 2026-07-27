/** Maximum character counts matching the backend API contract. */
export const LIMITS = {
  /** POST /chat message field */
  CHAT_MESSAGE_MAX: 40_000,
  /** Minimum query length for /search */
  SEARCH_QUERY_MIN: 2,
  /** Maximum query length for /search */
  SEARCH_QUERY_MAX: 500,
  /** Maximum capture text length */
  CAPTURE_TEXT_MAX: 40_000,
  /** Minimum capture text length */
  CAPTURE_TEXT_MIN: 10,
  /** Maximum recall answer length */
  RECALL_ANSWER_MAX: 4_000,
} as const;
