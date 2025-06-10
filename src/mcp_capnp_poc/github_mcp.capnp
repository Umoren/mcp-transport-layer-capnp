@0xb0a43a542c5ff8cf;

# GitHub-specific types
struct GitHubIssue {
  number @0 :UInt32;
  title @1 :Text;
  body @2 :Text;
  state @3 :Text;         # "open" or "closed"
  url @4 :Text;
  createdAt @5 :Text;
  updatedAt @6 :Text;
}

struct CreateIssueRequest {
  title @0 :Text;
  body @1 :Text;
}

struct ListIssuesRequest {
  state @0 :Text;         # "open", "closed", or "all"
  limit @1 :UInt32;       # max issues to return
}

struct GetIssueRequest {
  number @0 :UInt32;
}

# GitHub MCP Server interface
interface GitHubMcpServer {
  # Create a new issue
  createIssue @0 (request :CreateIssueRequest) -> (issue :GitHubIssue);
  
  # List issues from repository
  listIssues @1 (request :ListIssuesRequest) -> (issues :List(GitHubIssue));
  
  # Get specific issue by number
  getIssue @2 (request :GetIssueRequest) -> (issue :GitHubIssue);
  
  # Health check
  ping @3 () -> (pong :Text);
}