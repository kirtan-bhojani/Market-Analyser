/** Demo access credentials, prefilled on the auth pages so an interviewer can
 * sign in without provisioning an account. The "ID" is a real email string
 * under the hood — Supabase auth requires email format — but is presented to
 * the user as an "ID" (no email is asked for).
 *
 * A matching Supabase account MUST exist for these to actually sign in.
 * Change both here and in Supabase together. */
export const DEMO_ID = "demo@marketassistant.app";
export const DEMO_PASSKEY = "demo1234";
