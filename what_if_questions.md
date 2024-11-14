# What if Questions

For Scanning:
Specific
What happens if I replace Sequential Scan with an Index Scan on table A?
What happens if I replace Sequential Scan with a BitMap Scan on table A?
What happens if I prevent the use of Sequential Scan for table A?

What happens if I replace Index Scan with a Sequential Scan on table A?
What happens if I replace Index Scan with a BitMap Scan on table A?
What happens if I prevent the use of Index Scan for table A?

What happens if I replace BitMap Scan with a Sequential Scan on table A?
What happens if I replace BitMap Scan with an Index Scan on table A?
What happens if I prevent the use of BitMap Scan for table A?

General (Use SQL Planner)
What happens if I don't use Sequential Scan at all?
What happens if I don't use Index Scan at all?
What happens if I don't use BitMap Scan at all?

For Joins:
Specific
What happens if I change Nested Loop Join to a Hash Join for table A and B?
What happens if I change Nested Loop Join to a Merge Join for table A and B?
What happens if I prevent the use of Nested Loop Join for table A and B?

What happens if I change Hash Join to a Nested Loop Join for table A and B?
What happens if I change Hash Join to a Merge Join for table A and B?
What happens if I prevent the use of Hash Join for table A and B?

What happens if I change Merge Join to a Nested Loop Join for table A and B?
What happens if I change Merge Join to a Hash Join for table A and B?
What happens if I prevent the use of Merge Join for table A and B?

General (Use SQL Planner)
What happens if I don't use Nested Loop Join at all?
What happens if I don't use Hash Join at all?
What happens if I don't use Merge Join at all?

