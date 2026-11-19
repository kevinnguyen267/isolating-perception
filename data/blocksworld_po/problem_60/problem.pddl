(define (problem blocksworld)
	(:domain blocksworld)
	(:objects
		blue - block
		green - block
		orange - block
		purple - block
		red - block
		yellow - block
		robot - robot
	)
	(:init (handempty robot)
		(ontable yellow)
		(on green yellow)
		(on red green)
		(clear red)
		(ontable orange)
		(on blue orange)
		(clear blue)

		(ontable purple)
		(clear purple)
	)
	(:goal (and (handempty robot)
		(ontable green)
		(on red green)
		(on purple red)
		(clear purple)
		(ontable yellow)
		(clear yellow)
		(ontable orange)
		(clear orange)

		(ontable blue)
		(clear blue)
	))
)