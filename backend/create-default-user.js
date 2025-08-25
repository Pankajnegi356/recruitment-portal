const { pool, testConnection } = require('./config/database');

async function createDefaultUser() {
  try {
    // Test connection first
    console.log('Testing database connection...');
    const connected = await testConnection();
    
    if (!connected) {
      console.error('❌ Cannot connect to database');
      process.exit(1);
    }

    // Check if user with ID 1 already exists
    console.log('Checking for existing default user...');
    const [existingUsers] = await pool.execute('SELECT id, email FROM users WHERE id = 1');
    
    if (existingUsers.length > 0) {
      console.log('✅ Default user already exists:', existingUsers[0].email);
      process.exit(0);
    }

    // Create default admin user
    console.log('Creating default admin user...');
    const [result] = await pool.execute(`
      INSERT INTO users (id, first_name, last_name, email, password_hash, role, status, created_at)
      VALUES (1, 'Admin', 'User', 'admin@veersa.com', '$2b$12$defaultHashForDevelopment', 'admin', 'active', NOW())
    `);

    console.log('✅ Default user created successfully');
    console.log('📧 Email: admin@veersa.com');
    console.log('👤 Name: Admin User');
    console.log('🔑 Role: admin');

    // Verify the user was created
    const [newUser] = await pool.execute('SELECT * FROM users WHERE id = 1');
    console.log('User details:', {
      id: newUser[0].id,
      name: `${newUser[0].first_name} ${newUser[0].last_name}`,
      email: newUser[0].email,
      role: newUser[0].role,
      status: newUser[0].status
    });

  } catch (error) {
    console.error('❌ Error creating default user:', error);
    
    if (error.code === 'ER_DUP_ENTRY') {
      console.log('ℹ️  User already exists, this is normal');
    } else {
      console.error('Error details:', error.message);
    }
  } finally {
    // Close the connection
    process.exit(0);
  }
}

// Run the script
createDefaultUser();
