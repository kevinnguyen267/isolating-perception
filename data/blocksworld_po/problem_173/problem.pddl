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
		(ontable blue)
		(on purple blue)
		(clear purple)
		(ontable orange)
		(on red orange)
		(clear red)

		(ontable yellow)
		(clear yellow)
		(ontable green)
		(clear green)
	)
	(:goal (and (handempty robot)
		(ontable red)
		(on yellow red)
		(clear yellow)
		(ontable purple)
		(on orange purple)
		(clear orange)

		(ontable green)
		(on blue green)
		(clear blue)
	))
)