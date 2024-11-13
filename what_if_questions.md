# What if Questions

For Scanning:
Specific
What happens if I change the Sequential scan of table A to an Index Scan?
What happens if I change the Sequential scan of table A to a BitMap Scan?
What happens if I prevent the use of Sequential Scan for table A?

What happens if I change the Index Scan of table A to a Sequential Scan?
What happens if I change the Index Scan of table A to a BitMap Scan?
What happens if I prevent the use of Index Scan for table A?

What happens if I change the BitMap Scan of table A to a Sequential Scan?
What happens if I change the BitMap Scan of table A to an Index Scan?
What happens if I prevent the use of BitMap Scan for table A?

General (Use SQL Planner)
What happens if I don't use Sequential Scan at all?
What happens if I don't use Index Scan at all?
What happens if I don't use BitMap Scan at all?

For Joins:
Specific
What happens if I change the Nested Loop Join of table A and B to a Hash Join?
What happens if I change the Nested Loop Join of table A and B to a Merge Join?
What happens if I prevent the use of Nested Loop Join for table A and B?

What happens if I change the Hash Join of table A and B to a Nested Loop Join?
What happens if I change the Hash Join of table A and B to a Merge Join?
What happens if I prevent the use of Hash Join for table A and B?

What happens if I change the Merge Join of table A and B to a Nested Loop Join?
What happens if I change the Merge Join of table A and B to a Hash Join?
What happens if I prevent the use of Merge Join for table A and B?

General (Use SQL Planner)
What happens if I don't use Nested Loop Join at all?
What happens if I don't use Hash Join at all?
What happens if I don't use Merge Join at all?

