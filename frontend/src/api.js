// Frontend API Client

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://livekit-outbound-api.tinysaas.fun';

export async function getStats() {
  try {
    const response = await fetch(`${API_BASE_URL}/dashboard/stats`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error("Failed to fetch stats:", error);
    return null;
  }
}

export async function getAnalyticsVolume(days = 30) {
  try {
    const response = await fetch(`${API_BASE_URL}/dashboard/analytics/volume?days=${days}`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error("Failed to fetch analytics:", error);
    return [];
  }
}

export async function getRecentCalls(limit = 10) {
  try {
    const response = await fetch(`${API_BASE_URL}/dashboard/calls?limit=${limit}`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data.map(call => {
      if (call.recording_url && !call.recording_url.startsWith('http')) {
        call.recording_url = `${API_BASE_URL}${call.recording_url.startsWith('/') ? '' : '/'}${call.recording_url}`;
      }
      return call;
    });
  } catch (error) {
    console.error("Failed to fetch calls:", error);
    return [];
  }
}

// Get all prompts
export const getAllPrompts = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/dashboard/prompts`);
    if (!response.ok) throw new Error('Failed to fetch prompts');
    return await response.json();
  } catch (error) {
    console.error('Error fetching prompts:', error);
    return [];
  }
};

// Get active prompt
export const getActivePrompt = async (name = "default_roofing_agent") => {
  try {
    const response = await fetch(`${API_BASE_URL}/dashboard/prompt?name=${name}`);
    if (!response.ok) throw new Error('Failed to fetch prompt');
    return await response.json();
  } catch (error) {
    console.error('Error fetching prompt:', error);
    return null;
  }
};

// Update active prompt
export const updateActivePrompt = async (content, name = "default_roofing_agent") => {
  try {
    const response = await fetch(`${API_BASE_URL}/dashboard/prompt`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
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
    const response = await fetch(`${API_BASE_URL}/dashboard/call/${callId}`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    if (data && data.recording_url && !data.recording_url.startsWith('http')) {
      data.recording_url = `${API_BASE_URL}${data.recording_url.startsWith('/') ? '' : '/'}${data.recording_url}`;
    }
    return data;
  } catch (error) {
    console.error(`Failed to fetch call details for ${callId}:`, error);
    return null;
  }
}

export async function startOutboundCall(phoneNumber, businessName = "Default Business", agentSlug = "default_roofing_agent") {
  try {
    const response = await fetch(`${API_BASE_URL}/outbound-call`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        phone_number: phoneNumber,
        business_name: businessName,
        agent_slug: agentSlug
      }),
    });
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error("Failed to start call:", error);
    throw error;
  }
}
