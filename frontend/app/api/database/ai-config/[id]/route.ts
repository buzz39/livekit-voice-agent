import { NextRequest, NextResponse } from 'next/server';
import pool from '@/utils/db';

export async function DELETE(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
    let client;
    try {
        client = await pool.connect();
        const { id } = await params;
        if (!id) {
            return NextResponse.json({ error: 'ID is required' }, { status: 400 });
        }
        await client.query(`DELETE FROM ai_configs WHERE id = $1`, [parseInt(id)]);
        console.log('AI config deleted:', id);
        return NextResponse.json({ success: true });
    } catch (error: any) {
        console.error('Database error:', error);
        return NextResponse.json({ error: error.message || 'Failed to delete AI config' }, { status: 500 });
    } finally {
        if (client) {
            client.release();
        }
    }
}
