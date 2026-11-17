from app.database import get_db

def get_projects_for_user(current_user: dict) -> list:
    """
    Returns list of projects accessible to current_user according to RBAC:
    ADMIN -> all projects
    MANAGER -> projects with manager_id == current_user.id
    AGENT -> distinct projects containing their assigned tasks
    """
    role = current_user.get("role")
    user_id = current_user.get("id")
    conn = get_db()
    
    try:
        cursor = conn.cursor()
        if role == "ADMIN":
            cursor.execute("""
                SELECT p.*, u.name as manager_name,
                       (SELECT COUNT(*) FROM tasks t WHERE t.project_id = p.id) as task_count,
                       (SELECT COALESCE(SUM(t.estimated_hours), 0) FROM tasks t WHERE t.project_id = p.id) as total_hours
                FROM projects p
                JOIN users u ON p.manager_id = u.id
                ORDER BY p.deadline ASC, p.name ASC
            """)
        elif role == "MANAGER":
            cursor.execute("""
                SELECT p.*, u.name as manager_name,
                       (SELECT COUNT(*) FROM tasks t WHERE t.project_id = p.id) as task_count,
                       (SELECT COALESCE(SUM(t.estimated_hours), 0) FROM tasks t WHERE t.project_id = p.id) as total_hours
                FROM projects p
                JOIN users u ON p.manager_id = u.id
                WHERE p.manager_id = ?
                ORDER BY p.deadline ASC, p.name ASC
            """, (user_id,))
        elif role == "AGENT":
            cursor.execute("""
                SELECT DISTINCT p.*, u.name as manager_name,
                       (SELECT COUNT(*) FROM tasks t WHERE t.project_id = p.id AND t.assignee_id = ?) as task_count,
                       (SELECT COALESCE(SUM(t.estimated_hours), 0) FROM tasks t WHERE t.project_id = p.id AND t.assignee_id = ?) as total_hours
                FROM projects p
                JOIN users u ON p.manager_id = u.id
                JOIN tasks t ON t.project_id = p.id
                WHERE t.assignee_id = ?
                ORDER BY p.deadline ASC, p.name ASC
            """, (user_id, user_id, user_id))
        else:
            return []
        
        rows = cursor.fetchall()
        projects = []
        for r in rows:
            projects.append({
                "id": r["id"],
                "name": r["name"],
                "clientName": r["client_name"],
                "description": r["description"],
                "managerId": r["manager_id"],
                "managerName": r["manager_name"],
                "deadline": r["deadline"],
                "taskCount": r["task_count"],
                "totalHours": float(r["total_hours"]),
                "createdAt": r["created_at"]
            })
        return projects
    finally:
        conn.close()

def get_tasks_for_project(current_user: dict, project_id: str) -> list:
    """
    Returns tasks for project according to RBAC:
    ADMIN -> all tasks in project_id
    MANAGER -> all tasks only if they manage project_id
    AGENT -> only tasks assigned to them in project_id
    """
    role = current_user.get("role")
    user_id = current_user.get("id")
    conn = get_db()
    
    try:
        cursor = conn.cursor()
        
        # First verify project existence and manager
        cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        proj = cursor.fetchone()
        if not proj:
            return None
        
        if role == "ADMIN":
            cursor.execute("""
                SELECT t.*, u.name as assignee_name, u.role as assignee_role, u.specialization as assignee_spec
                FROM tasks t
                JOIN users u ON t.assignee_id = u.id
                WHERE t.project_id = ?
                ORDER BY t.deadline ASC, t.title ASC
            """, (project_id,))
        elif role == "MANAGER":
            if proj["manager_id"] != user_id:
                # Manager does not manage this project
                return None
            cursor.execute("""
                SELECT t.*, u.name as assignee_name, u.role as assignee_role, u.specialization as assignee_spec
                FROM tasks t
                JOIN users u ON t.assignee_id = u.id
                WHERE t.project_id = ?
                ORDER BY t.deadline ASC, t.title ASC
            """, (project_id,))
        elif role == "AGENT":
            cursor.execute("""
                SELECT t.*, u.name as assignee_name, u.role as assignee_role, u.specialization as assignee_spec
                FROM tasks t
                JOIN users u ON t.assignee_id = u.id
                WHERE t.project_id = ? AND t.assignee_id = ?
                ORDER BY t.deadline ASC, t.title ASC
            """, (project_id, user_id))
        else:
            return None
            
        rows = cursor.fetchall()
        tasks = []
        for r in rows:
            tasks.append({
                "id": r["id"],
                "projectId": r["project_id"],
                "title": r["title"],
                "description": r["description"],
                "assigneeId": r["assignee_id"],
                "assigneeName": r["assignee_name"],
                "assigneeRole": r["assignee_role"],
                "assigneeSpecialization": r["assignee_spec"],
                "deadline": r["deadline"],
                "estimatedHours": float(r["estimated_hours"]),
                "createdAt": r["created_at"]
            })
        return tasks
    finally:
        conn.close()

def get_project_by_id(current_user: dict, project_id: str) -> dict:
    """
    getProjectById(currentUser, projectId):
    reject if project is outside getProjects(currentUser)
    return project details with getTasks(currentUser, projectId)
    """
    # 1. Check if allowed in getProjects
    allowed_projects = get_projects_for_user(current_user)
    matching_project = next((p for p in allowed_projects if p["id"] == project_id), None)
    if not matching_project:
        return None
    
    # 2. Get filtered tasks
    tasks = get_tasks_for_project(current_user, project_id)
    if tasks is None:
        return None
    
    matching_project["tasks"] = tasks
    return matching_project

def get_user_tasks_summary(current_user: dict) -> list:
    """
    Returns the list of tasks for the 'My Tasks' screen filtered by role:
    ADMIN -> all tasks across all projects
    MANAGER -> all tasks in projects they manage
    AGENT -> only tasks assigned to current_user
    """
    role = current_user.get("role")
    user_id = current_user.get("id")
    conn = get_db()
    
    try:
        cursor = conn.cursor()
        query = """
            SELECT t.*, p.name as project_name, p.client_name, u.name as assignee_name, u.specialization as assignee_spec
            FROM tasks t
            JOIN projects p ON t.project_id = p.id
            JOIN users u ON t.assignee_id = u.id
        """
        params = []
        
        if role == "ADMIN":
            query += " ORDER BY t.deadline ASC, p.name ASC"
        elif role == "MANAGER":
            query += " WHERE p.manager_id = ? ORDER BY t.deadline ASC, p.name ASC"
            params.append(user_id)
        elif role == "AGENT":
            query += " WHERE t.assignee_id = ? ORDER BY t.deadline ASC, p.name ASC"
            params.append(user_id)
        else:
            return []
            
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        tasks = []
        for r in rows:
            tasks.append({
                "id": r["id"],
                "projectId": r["project_id"],
                "projectName": r["project_name"],
                "clientName": r["client_name"],
                "title": r["title"],
                "description": r["description"],
                "assigneeId": r["assignee_id"],
                "assigneeName": r["assignee_name"],
                "assigneeSpecialization": r["assignee_spec"],
                "deadline": r["deadline"],
                "estimatedHours": float(r["estimated_hours"]),
                "createdAt": r["created_at"]
            })
        return tasks
    finally:
        conn.close()
