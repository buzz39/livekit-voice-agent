// Frontend API Client

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://livekit-outbound-api.tinysaas.fun';
export const apiEvents = new EventTarget();

function emitApiError(message) {
  apiEvents.dispatchEvent(new CustomEvent('error', { detail: { message } }));
}

// Helper to get Stack Auth session token
async function getAuthHeaders() {
  try {
    // Stack Auth stores the app instance on window after initialization
    if (window.__stackClientApp) {
      const user = await window.__stackClientApp.getUser();
      if (user) {
        const token = await user.getAuthJson();
        if (token?.accessToken) {
          return { 'Authorization': `Bearer ${token.accessToken}` };
        }
      }
    }
  } catch {
    // Silently fail — auth headers are optional until backend enforces them
  }
  return {};
}

async function apiFetch(path, options = {}) {
  const authHeaders = await getAuthHeaders();
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders,
      ...(options.headers || {}),
    },
  });
  return response;
}

export async function getStats() {
  try {
    const response = await apiFetch('/dashboard/stats');
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return await response.json();
  } catch (error) {
    console.error("Failed to fetch stats:", error);
    emitApiError('Unable to load dashboard stats right now.');
    return null;
  }
}

export async function getAnalyticsVolume(days = 30) {
  try {
    const response = await apiFetch(`/dashboard/analytics/volume?days=${days}`);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return await response.json();
  } catch (error) {
    console.error("Failed to fetch analytics:", error);
    emitApiError('Unable to load analytics right now.');
    return [];
  }
}

export async function getRecentCalls(limit = 10) {
  try {
    const response = await apiFetch(`/dashboard/calls?limit=${limit}`);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const data = await response.json();
    return data.map(call => {
      if (call.recording_url && !call.recording_url.startsWith('http')) {
        call.recording_url = `${API_BASE_URL}${call.recording_url.startsWith('/') ? '' : '/'}${call.recording_url}`;
      }
      return call;
    });
  } catch (error) {
    console.error("Failed to fetch calls:", error);
    emitApiError('Unable to load recent calls right now.');
    return [];
  }
}

export async function getAppointments() {
  try {
    const response = await apiFetch('/dashboard/appointments');
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return await response.json();
  } catch (error) {
    console.error("Failed to fetch appointments:", error);
    emitApiError('Unable to load appointments right now.');
    return [];
  }
}

export const getAllPrompts = async () => {
  try {
    const response = await apiFetch('/dashboard/prompts');
    if (!response.ok) throw new Error('Failed to fetch prompts');
    return await response.json();
  } catch (error) {
    console.error('Error fetching prompts:', error);
    emitApiError('Unable to load prompts right now.');
    return [];
  }
};

export const getActivePrompt = async (name = "default_roofing_agent") => {
  try {
    const response = await apiFetch(`/dashboard/prompt?name=${name}`);
    if (!response.ok) throw new Error('Failed to fetch prompt');
    return await response.json();
  } catch (error) {
    console.error('Error fetching prompt:', error);
    emitApiError('Unable to load the current prompt right now.');
    return null;
  }
};

export const updateActivePrompt = async (content, name = "default_roofing_agent") => {
  try {
    const response = await apiFetch('/dashboard/prompt', {
      method: 'POST',
      body: JSON.stringify({ name, content }),
    });
    if (!response.ok) throw new Error('Failed to update prompt');
    return await response.json();
  } catch (error) {
    console.error('Error updating prompt:', error);
    throw error;
  }
};

export async function getCallDetails(callId) {
  try {
    const response = await apiFetch(`/dashboard/call/${callId}`);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const data = await response.json();
    if (data && data.recording_url && !data.recording_url.startsWith('http')) {
      data.recording_url = `${API_BASE_URL}${data.recording_url.startsWith('/') ? '' : '/'}${data.recording_url}`;
    }
    return data;
  } catch (error) {
    console.error(`Failed to fetch call details for ${callId}:`, error);
    emitApiError('Unable to load call details right now.');
    return null;
  }
}

export async function saveAgentConfig(config) {
  const response = await apiFetch('/api/config', {
    method: 'POST',
    body: JSON.stringify(config),
  });
  if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
  return await response.json();
}

export async function startOutboundCall(phoneNumber, businessName = "Default Business", agentSlug = "default_roofing_agent") {
  try {
    const response = await apiFetch('/outbound-call', {
      method: 'POST',
      body: JSON.stringify({
        phone_number: phoneNumber,
        business_name: businessName,
        agent_slug: agentSlug,
      }),
    });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return await response.json();
  } catch (error) {
    console.error("Failed to start call:", error);
    throw error;
  }
}
