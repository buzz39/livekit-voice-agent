import { Pool } from '@neondatabase/serverless';
import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
    const { url } = await request.json();

    if (!url) {
        return NextResponse.json({ error: 'Database URL required' }, { status: 400 });
    }

    let client;
    try {
        // Create a new pool with the provided URL
        const pool = new Pool({ connectionString: url });
        client = await pool.connect();

        // Test the connection
        await client.query('SELECT 1');
        await client.release();

        // Get all tables and their columns
        const tablesQuery = `
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        `;

        client = await pool.connect();
        const tablesResult = await client.query(tablesQuery);
        const tableNames = tablesResult.rows.map((row: any) => row.table_name);

        // Get columns and data for each table
        const tables = [];
        for (const tableName of tableNames) {
            try {
                // Get columns
                const columnsQuery = `
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_schema = 'public' AND table_name = $1
                    ORDER BY ordinal_position
                `;
                const columnsResult = await client.query(columnsQuery, [tableName]);
                const columns = columnsResult.rows.map((row: any) => row.column_name);

                // Get rows
                const dataQuery = `SELECT * FROM ${tableName} LIMIT 1000`;
                const dataResult = await client.query(dataQuery);
                const rows = dataResult.rows;

                tables.push({
                    name: tableName,
                    columns,
                    rows,
                });
            } catch (e: any) {
                console.error(`Error getting data for table ${tableName}:`, e.message);
            }
        }

        await client.release();
        return NextResponse.json({ tables }, { status: 200 });
    } catch (error: any) {
        return NextResponse.json(
            { error: error.message || 'Failed to connect to database' },
            { status: 500 }
        );
    } finally {
        if (client) {
            try {
                await client.release();
            } catch (e) {
                // Ignore release errors
            }
        }
    }
}
