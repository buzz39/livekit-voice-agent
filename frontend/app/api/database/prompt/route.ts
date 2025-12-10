import { NextRequest, NextResponse } from 'next/server';
import pool from '@/utils/db';

export async function POST(request: NextRequest) {
    let client;
    try {
        client = await pool.connect();
        const data = await request.json();
        const { id, name, content, is_active, owner_id } = data;

        if (!name) {
            return NextResponse.json({ error: 'Name is required' }, { status: 400 });
        }

        if (id) {
            // Update
            await client.query(
                `UPDATE prompts SET content = $1, is_active = $2, updated_at = NOW()
                 WHERE id = $3`,
                [content || '', is_active ?? true, id]
            );
            console.log('Prompt updated:', id);
        } else {
            // Create
            await client.query(
                `INSERT INTO prompts (name, owner_id, content, is_active)
                 VALUES ($1, $2, $3, $4)`,
                [name, owner_id || 'dev_user', content || '', is_active ?? true]
            );
            console.log('Prompt created:', name);
        }

        return NextResponse.json({ success: true });
    } catch (error: any) {
        console.error('Database error:', error);
        return NextResponse.json({ error: error.message || 'Failed to save prompt' }, { status: 500 });
    } finally {
        if (client) {
            client.release();
        }
    }
}

export async function DELETE(request: NextRequest) {
    const client = await pool.connect();
    try {
        const body = await request.json();
        const { id } = body;
        await client.query(`DELETE FROM prompts WHERE id = $1`, [parseInt(id)]);
        return NextResponse.json({ success: true });
    } catch (error) {
        console.error('Database error:', error);
        return NextResponse.json({ error: 'Failed to delete prompt' }, { status: 500 });
    } finally {
        client.release();
    }
}
