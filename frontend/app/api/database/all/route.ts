import { NextRequest, NextResponse } from 'next/server';
import pool from '@/utils/db';

export async function GET() {
    let client;
    try {
        client = await pool.connect();
        
        // Fetch data with error handling for each table
        let agents = [];
        let ai_configs = [];
        let prompts = [];

        try {
            const agentsRes = await client.query(`SELECT * FROM agent_configs ORDER BY created_at DESC`);
            agents = agentsRes.rows;
            console.log('Fetched agents:', agents.length);
        } catch (e: any) {
            console.warn('agent_configs table error:', e.message);
        }

        try {
            const aiConfigsRes = await client.query(`SELECT * FROM ai_configs ORDER BY created_at DESC`);
            ai_configs = aiConfigsRes.rows;
            console.log('Fetched ai_configs:', ai_configs.length);
        } catch (e: any) {
            console.warn('ai_configs table error:', e.message);
        }

        try {
            const promptsRes = await client.query(`SELECT * FROM prompts ORDER BY created_at DESC`);
            prompts = promptsRes.rows;
            console.log('Fetched prompts:', prompts.length);
        } catch (e: any) {
            console.warn('prompts table error:', e.message);
        }

        return NextResponse.json({
            agents,
            ai_configs,
            prompts,
            message: 'Data loaded successfully'
        });
    } catch (error: any) {
        console.error('Database connection error:', error);
        return NextResponse.json({ 
            error: 'Failed to connect to database: ' + error.message,
            agents: [],
            ai_configs: [],
            prompts: []
        }, { status: 200 }); // Return 200 to avoid client-side errors
    } finally {
        if (client) {
            client.release();
        }
    }
}
