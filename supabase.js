// const SUPABASE_URL = "YOUR_SUPABASE_URL";
// const SUPABASE_ANON_KEY = "YOUR_SUPABASE_ANON_KEY";

// const supabaseClient = window.supabase.createClient(
//     SUPABASE_URL,
//     SUPABASE_ANON_KEY
// );

/* =========================================================
   QUIZONE - SUPABASE CONFIGURATION
   ========================================================= */
const SUPABASE_URL = "https://gpibipeixgczisajzdce.supabase.co";
const SUPABASE_ANON_KEY = "sb_publishable_NjuSHVB63Mx8NCS5e4-flQ_4eTpa-pC";

const supabaseClient = window.supabase.createClient(
    SUPABASE_URL,
    SUPABASE_ANON_KEY
);

// Get current logged-in user
async function getCurrentUser() {
    const { data, error } = await supabaseClient.auth.getUser();

    if (error) {
        return null;
    }

    return data.user;
}

// Normal login
async function loginUser(email, password) {
    return await supabaseClient.auth.signInWithPassword({
        email,
        password
    });
}

// Send OTP for account creation
async function sendSignupOtp(email, name) {
    return await supabaseClient.auth.signInWithOtp({
        email: email,
        options: {
            shouldCreateUser: true,
            data: {
                full_name: name
            }
        }
    });
}

// Verify signup OTP
async function verifySignupOtp(email, token) {
    return await supabaseClient.auth.verifyOtp({
        email: email,
        token: token,
        type: "email"
    });
}

// Create password after OTP verification
async function createUserPassword(password, name) {
    return await supabaseClient.auth.updateUser({
        password: password,
        data: {
            full_name: name
        }
    });
}

// Logout
async function logoutUser() {
    return await supabaseClient.auth.signOut();
}

// Auth state listener
function listenToAuthChanges(callback) {
    return supabaseClient.auth.onAuthStateChange(
        (event, session) => {
            callback(event, session);
        }
    );
}